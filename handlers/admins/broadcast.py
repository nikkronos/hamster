"""
Рассылка с поддержкой фото, dry-run, фильтра исключений и promo-кнопки.

Phase 1: фото + dry-run + список исключений.
Phase 3: + выбор промокода-кнопки, запись broadcast row в БД hamster26,
         inline-кнопка под рассылкой с deep link, второй тест на test-аккаунт.

ВАЖНО: все campaign-данные (broadcasts, broadcast_clicks) живут в БД hamster26.
Оба бота пишут туда напрямую через sqlite3 (absolute path).
"""
import asyncio
import datetime
import logging
import os
import sqlite3

from aiogram import types, utils
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from keyboards.keyboards import get_keyboard
from loader import dp
from utils import states_users as su
from data import config

logger = logging.getLogger(__name__)

# Файл исключений (локальный для каждого бота)
EXCLUDES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "broadcast_excludes.txt",
)

# Единая БД для кампаний (всегда hamster26)
CAMPAIGN_DB = "/home/hamster26/bot/database/database.sqlite"

# БД "соседнего" бота — для cross-bot фильтра (Phase 2)
HAMSTER93_DB = "/home/hamster93_bot/database/database.sqlite"

# Куда ведут deep link (бот-получатель)
TARGET_BOT_USERNAME = "hamster26_bot"

# Тестовый аккаунт владельца
TEST_USER_ID = 7882817110

# Имя текущего бота (для broadcasts.from_bot)
_path = os.path.abspath(__file__)
BOT_NAME = "hamster93" if "hamster93" in _path else "hamster26"


def get_hamster93_user_ids():
    """Возвращает set user_id'ов из БД hamster93. Для cross-bot dedup."""
    try:
        conn = sqlite3.connect(HAMSTER93_DB, timeout=10.0)
        try:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users")
            return {row[0] for row in cur.fetchall()}
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Не удалось прочитать hamster93 users: {e}")
        return set()


# ============================================================================
# Файл исключений
# ============================================================================

def load_exclude_ids():
    if not os.path.exists(EXCLUDES_FILE):
        return set()
    try:
        with open(EXCLUDES_FILE, "r", encoding="utf-8") as f:
            return {int(line.strip()) for line in f if line.strip().isdigit()}
    except Exception as e:
        logger.error(f"Не удалось прочитать {EXCLUDES_FILE}: {e}")
        return set()


async def get_recipients(audience_type):
    all_users = await get_data("users", fetch="all") or []
    active_subs = await get_data("user_subscriptions", fetch="all") or []
    active_ids = {sub["user_id"] for sub in active_subs}
    exclude_ids = load_exclude_ids()

    if audience_type == "active":
        recipients = [u["user_id"] for u in all_users if u["user_id"] in active_ids]
    elif audience_type == "inactive":
        recipients = [u["user_id"] for u in all_users if u["user_id"] not in active_ids]
    elif audience_type == "unique":
        # Только те, кого НЕТ в hamster93 (для hamster26)
        h93_ids = get_hamster93_user_ids()
        recipients = [u["user_id"] for u in all_users if u["user_id"] not in h93_ids]
    else:
        recipients = [u["user_id"] for u in all_users]

    recipients = [uid for uid in recipients if uid not in exclude_ids]
    return recipients, len(exclude_ids)


# ============================================================================
# Cross-DB helpers (для записи в БД hamster26)
# ============================================================================

def _now_ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def campaign_list_promocodes():
    """Возвращает [(id, code, percent, expiration), ...] из БД hamster26"""
    conn = sqlite3.connect(CAMPAIGN_DB, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, promocode, percent, expiration FROM promocodes ORDER BY id DESC LIMIT 20"
        )
        return cur.fetchall()
    finally:
        conn.close()


def campaign_get_promocode_by_id(promo_id):
    conn = sqlite3.connect(CAMPAIGN_DB, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("SELECT promocode FROM promocodes WHERE id = ?", (promo_id,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def campaign_create_broadcast(from_bot, audience, promocode, has_photo, preview, recipients):
    conn = sqlite3.connect(CAMPAIGN_DB, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO broadcasts
               (from_bot, audience, promocode, has_photo, preview, recipients,
                delivered, blocked, failed, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, ?, NULL)""",
            (from_bot, audience, promocode, has_photo, preview, recipients, _now_ts()),
        )
        bid = cur.lastrowid
        conn.commit()
        return bid
    finally:
        conn.close()


def campaign_update_broadcast(broadcast_id, delivered, blocked, failed):
    conn = sqlite3.connect(CAMPAIGN_DB, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE broadcasts SET delivered=?, blocked=?, failed=?, completed_at=? WHERE id=?",
            (delivered, blocked, failed, _now_ts(), broadcast_id),
        )
        conn.commit()
    finally:
        conn.close()


def campaign_delete_broadcast(broadcast_id):
    conn = sqlite3.connect(CAMPAIGN_DB, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM broadcasts WHERE id = ?", (broadcast_id,))
        conn.commit()
    finally:
        conn.close()


def make_promo_button_markup(broadcast_id, label="🎁 Получить скидку"):
    url = f"https://t.me/{TARGET_BOT_USERNAME}?start=p{broadcast_id}"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text=label, url=url))
    return kb


# ============================================================================
# Меню рассылки — шаг 1: аудитория
# ============================================================================

@dp.callback_query_handler(Text("broadcast"), state="*")
async def broadcast_menu(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return
    # Чистим состояние и старый broadcast_id если был (защита от мусорных rows)
    old_bid = await su.get_data_from_state(call.from_user.id, "broadcast_id")
    if old_bid:
        try:
            campaign_delete_broadcast(old_bid)
        except Exception:
            pass
    await su.reset_state_user(call.from_user.id, clear_data=True)

    buttons = [
        [("Все пользователи", "baud_all")],
        [("Только активные", "baud_active")],
        [("Только неактивные", "baud_inactive")],
    ]
    # Cross-bot фильтр — только для hamster26
    if BOT_NAME == "hamster26":
        buttons.append([("Только не в hamster93 (уникальные)", "baud_unique")])
    buttons.append([("Отмена", "menu_admin")])

    await call.message.answer(
        "📢 <b>Рассылка</b>\n\nВыберите аудиторию:",
        reply_markup=await get_keyboard(buttons),
        parse_mode="HTML",
    )


# ============================================================================
# Шаг 2: после аудитории — спрашиваем про промокод-кнопку
# ============================================================================

@dp.callback_query_handler(Text(startswith="baud_"), state="*")
async def broadcast_select_audience(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return

    audience = call.data.replace("baud_", "")
    await su.save_data_state(call.from_user.id, broadcast_audience=audience)

    buttons = [
        [("📭 Без кнопки", "bpromo_none")],
        [("🎁 С кнопкой скидки", "bpromo_select")],
        [("Отмена", "broadcast_cancel")],
    ]
    await call.message.answer(
        "Прикрепить под рассылкой кнопку-промокод?\n\n"
        "• <b>Без кнопки</b> — обычная рассылка\n"
        "• <b>С кнопкой скидки</b> — добавит inline-кнопку, "
        "клик откроет hamster26 и применит выбранный промокод",
        reply_markup=await get_keyboard(buttons),
        parse_mode="HTML",
    )


@dp.callback_query_handler(Text("bpromo_none"), state="*")
async def broadcast_no_promo(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return
    await su.save_data_state(call.from_user.id, broadcast_promo=None)
    await _ask_message_type(call.message)


@dp.callback_query_handler(Text("bpromo_select"), state="*")
async def broadcast_select_promo(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return

    promos = campaign_list_promocodes()
    if not promos:
        await call.message.answer(
            "⚠️ Промокодов в БД нет. Создай через 'Создать промокод' сначала.",
            reply_markup=await get_keyboard([[("Назад", "broadcast")]]),
        )
        return

    buttons = []
    for pid, code, percent, exp in promos:
        try:
            exp_short = (exp or "").split(" ")[0]
        except Exception:
            exp_short = "—"
        label = f"{code} ({percent}%, до {exp_short})"
        buttons.append([(label, f"bpcode_{pid}")])
    buttons.append([("Отмена", "broadcast_cancel")])

    await call.message.answer(
        "Выбери промокод для кнопки:",
        reply_markup=await get_keyboard(buttons),
    )


@dp.callback_query_handler(Text(startswith="bpcode_"), state="*")
async def broadcast_promo_chosen(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return

    promo_id = int(call.data.replace("bpcode_", ""))
    promo_code = campaign_get_promocode_by_id(promo_id)
    if not promo_code:
        await call.message.answer("⚠️ Промокод не найден.")
        return

    await su.save_data_state(call.from_user.id, broadcast_promo=promo_code)
    await call.message.answer(
        f"✅ Выбран промокод: <b>{promo_code}</b>",
        parse_mode="HTML",
    )
    await _ask_message_type(call.message)


async def _ask_message_type(message):
    buttons = [
        [("📝 Только текст", "btype_text")],
        [("🖼 Фото + подпись", "btype_photo")],
        [("Отмена", "broadcast_cancel")],
    ]
    await message.answer("Тип сообщения:", reply_markup=await get_keyboard(buttons))


# ============================================================================
# Шаг 3: контент (текст или фото)
# ============================================================================

@dp.callback_query_handler(Text("btype_text"), state="*")
async def broadcast_ask_text(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return
    buttons = [[("Отмена", "broadcast_cancel")]]
    await call.message.answer(
        "Отправьте текст сообщения.\n\nПоддерживается HTML.",
        reply_markup=await get_keyboard(buttons),
    )
    await su.set_state(call.from_user.id, "broadcast_wait_text")


@dp.message_handler(state="broadcast_wait_text")
async def broadcast_receive_text(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        await su.reset_state_user(message.from_user.id, clear_data=True)
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст не может быть пустым.")
        return
    await su.save_data_state(message.from_user.id, broadcast_text=text, broadcast_photo=None)
    await _show_confirmation(message, has_photo=False)


@dp.callback_query_handler(Text("btype_photo"), state="*")
async def broadcast_ask_photo(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return
    buttons = [[("Отмена", "broadcast_cancel")]]
    await call.message.answer(
        "📷 Отправьте фото.\n(Можно сразу с подписью.)",
        reply_markup=await get_keyboard(buttons),
    )
    await su.set_state(call.from_user.id, "broadcast_wait_photo")


@dp.message_handler(state="broadcast_wait_photo", content_types=types.ContentTypes.PHOTO)
async def broadcast_receive_photo(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        await su.reset_state_user(message.from_user.id, clear_data=True)
        return
    file_id = message.photo[-1].file_id
    await su.save_data_state(message.from_user.id, broadcast_photo=file_id)

    if message.caption:
        caption = message.caption.strip()
        if len(caption) > 1024:
            await message.answer(
                f"⚠️ Подпись слишком длинная: {len(caption)} симв. (лимит 1024). "
                f"Пришлите подпись отдельным сообщением:"
            )
            await su.set_state(message.from_user.id, "broadcast_wait_caption")
            return
        await su.save_data_state(message.from_user.id, broadcast_text=caption)
        await _show_confirmation(message, has_photo=True)
        return

    buttons = [[("Отмена", "broadcast_cancel")]]
    await message.answer(
        "✅ Фото получено. Теперь подпись (до 1024 симв).",
        reply_markup=await get_keyboard(buttons),
    )
    await su.set_state(message.from_user.id, "broadcast_wait_caption")


@dp.message_handler(state="broadcast_wait_photo")
async def broadcast_wait_photo_wrong(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return
    await message.answer("⚠️ Это не фото. Пришлите изображение.")


@dp.message_handler(state="broadcast_wait_caption")
async def broadcast_receive_caption(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        await su.reset_state_user(message.from_user.id, clear_data=True)
        return
    caption = (message.text or "").strip()
    if not caption:
        await message.answer("Подпись не может быть пустой.")
        return
    if len(caption) > 1024:
        await message.answer(f"⚠️ {len(caption)} симв., лимит 1024.")
        return
    await su.save_data_state(message.from_user.id, broadcast_text=caption)
    await _show_confirmation(message, has_photo=True)


# ============================================================================
# Шаг 4: подтверждение + создание broadcast row + кнопки тест/отправить
# ============================================================================

async def _show_confirmation(message: types.Message, has_photo: bool):
    admin_id = message.from_user.id
    audience = await su.get_data_from_state(admin_id, "broadcast_audience")
    text = await su.get_data_from_state(admin_id, "broadcast_text")
    photo = await su.get_data_from_state(admin_id, "broadcast_photo") if has_photo else None
    promo = await su.get_data_from_state(admin_id, "broadcast_promo")

    recipients, excluded_count = await get_recipients(audience)

    # Создаём broadcast row (ID нужен для inline кнопки)
    bid = await su.get_data_from_state(admin_id, "broadcast_id")
    if not bid:
        bid = campaign_create_broadcast(
            from_bot=BOT_NAME,
            audience=audience,
            promocode=promo,
            has_photo=1 if has_photo else 0,
            preview=(text or "")[:500],
            recipients=len(recipients),
        )
        await su.save_data_state(admin_id, broadcast_id=bid)
        logger.info(f"Created broadcast row id={bid} by admin {admin_id}")

    audience_label = {
        "all": "все пользователи",
        "active": "только активные подписчики",
        "inactive": "только неактивные (без подписки)",
        "unique": "только не в hamster93 (уникальные для hamster26)",
    }.get(audience, audience)

    preview_text = text[:500] + ("…" if len(text) > 500 else "")
    promo_line = f"<b>Промокод-кнопка:</b> {promo}\n" if promo else "<b>Промокод-кнопка:</b> нет\n"
    info = (
        f"📋 <b>Подтверждение рассылки #{bid}</b>\n\n"
        f"<b>Бот-отправитель:</b> {BOT_NAME}\n"
        f"<b>Аудитория:</b> {audience_label}\n"
        f"<b>Получателей:</b> {len(recipients)}\n"
        f"<b>Исключено по списку:</b> {excluded_count}\n"
        f"<b>Тип:</b> {'фото + подпись' if has_photo else 'только текст'}\n"
        f"{promo_line}\n"
        f"<b>Превью:</b>\n{preview_text}"
    )

    buttons = [
        [("🧪 Тест себе", "bsend_test_self")],
        [(f"🧪 Тест на {TEST_USER_ID}", "bsend_test_user")],
        [("✅ Отправить всем", "bsend_all")],
        [("❌ Отмена", "broadcast_cancel")],
    ]

    if has_photo and photo:
        await message.answer_photo(
            photo=photo,
            caption=info,
            reply_markup=await get_keyboard(buttons),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            info,
            reply_markup=await get_keyboard(buttons),
            parse_mode="HTML",
        )


# ============================================================================
# Отправка
# ============================================================================

async def _send_one(user_id, text, photo, broadcast_id, with_promo_button):
    reply_markup = make_promo_button_markup(broadcast_id) if with_promo_button else None
    try:
        if photo:
            await dp.bot.send_photo(
                chat_id=user_id, photo=photo, caption=text,
                parse_mode="HTML", reply_markup=reply_markup,
            )
        else:
            await dp.bot.send_message(
                chat_id=user_id, text=text,
                parse_mode="HTML", reply_markup=reply_markup,
            )
        return "sent"
    except utils.exceptions.BotBlocked:
        return "blocked"
    except utils.exceptions.RetryAfter as e:
        logger.warning(f"RetryAfter {e.timeout}s uid={user_id}")
        await asyncio.sleep(e.timeout)
        try:
            if photo:
                await dp.bot.send_photo(
                    chat_id=user_id, photo=photo, caption=text,
                    parse_mode="HTML", reply_markup=reply_markup,
                )
            else:
                await dp.bot.send_message(
                    chat_id=user_id, text=text,
                    parse_mode="HTML", reply_markup=reply_markup,
                )
            return "sent"
        except Exception as e2:
            logger.error(f"Retry failed for {user_id}: {e2}")
            return "failed"
    except Exception as e:
        logger.error(f"Send fail {user_id}: {e}")
        return "failed"


async def _do_test_send(call: types.CallbackQuery, recipient_uid: int):
    admin_id = call.from_user.id
    text = await su.get_data_from_state(admin_id, "broadcast_text")
    photo = await su.get_data_from_state(admin_id, "broadcast_photo")
    promo = await su.get_data_from_state(admin_id, "broadcast_promo")
    bid = await su.get_data_from_state(admin_id, "broadcast_id")

    if not text or not bid:
        await call.message.answer("⚠️ Данные не найдены. Начни заново через /admin.")
        return

    status = await _send_one(recipient_uid, text, photo, bid, with_promo_button=bool(promo))

    after_buttons = [
        [("🧪 Тест себе", "bsend_test_self")],
        [(f"🧪 Тест на {TEST_USER_ID}", "bsend_test_user")],
        [("✅ Отправить всем", "bsend_all")],
        [("❌ Отмена", "broadcast_cancel")],
    ]
    if status == "sent":
        await call.message.answer(
            f"🧪 Тест отправлен на <code>{recipient_uid}</code>.\n\n"
            f"Если всё ок — жми «Отправить всем».\n"
            f"Иначе — «Отмена» и заново.",
            reply_markup=await get_keyboard(after_buttons),
            parse_mode="HTML",
        )
    else:
        await call.message.answer(
            f"⚠️ Тест не прошёл (статус: {status}).\n"
            f"Возможно: HTML битый, или получатель заблокировал бота.",
            reply_markup=await get_keyboard(after_buttons),
        )


@dp.callback_query_handler(Text("bsend_test_self"), state="*")
async def broadcast_test_self(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return
    await _do_test_send(call, call.from_user.id)


@dp.callback_query_handler(Text("bsend_test_user"), state="*")
async def broadcast_test_user(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return
    await _do_test_send(call, TEST_USER_ID)


@dp.callback_query_handler(Text("bsend_all"), state="*")
async def broadcast_send_all(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        await su.reset_state_user(call.from_user.id, clear_data=True)
        return

    admin_id = call.from_user.id
    audience = await su.get_data_from_state(admin_id, "broadcast_audience")
    text = await su.get_data_from_state(admin_id, "broadcast_text")
    photo = await su.get_data_from_state(admin_id, "broadcast_photo")
    promo = await su.get_data_from_state(admin_id, "broadcast_promo")
    bid = await su.get_data_from_state(admin_id, "broadcast_id")
    await su.reset_state_user(admin_id, clear_data=True)

    if not text or not bid:
        await call.message.answer("⚠️ Данные не найдены.")
        return

    recipients, _ = await get_recipients(audience)
    if not recipients:
        await call.message.answer("⚠️ Нет получателей.")
        try:
            campaign_delete_broadcast(bid)
        except Exception:
            pass
        return

    total = len(recipients)
    with_promo = bool(promo)
    progress_msg = await call.message.answer(
        f"🚀 Запускаю рассылку #{bid} для {total} пользователей…"
    )

    sent = blocked = failed = 0
    for i, uid in enumerate(recipients, 1):
        status = await _send_one(uid, text, photo, bid, with_promo_button=with_promo)
        if status == "sent":
            sent += 1
        elif status == "blocked":
            blocked += 1
        else:
            failed += 1

        if i % 20 == 0:
            await asyncio.sleep(1)
        else:
            await asyncio.sleep(0.05)

        if i % 50 == 0:
            try:
                await progress_msg.edit_text(
                    f"⏳ Рассылка #{bid}…\n"
                    f"Отправлено: {sent}/{total}\n"
                    f"Заблокировали: {blocked}\n"
                    f"Ошибок: {failed}"
                )
            except Exception:
                pass

    try:
        campaign_update_broadcast(bid, sent, blocked, failed)
    except Exception as e:
        logger.error(f"Не удалось обновить broadcasts row {bid}: {e}")

    report = (
        f"✅ <b>Рассылка #{bid} завершена</b>\n\n"
        f"Всего: {total}\n"
        f"Доставлено: {sent}\n"
        f"Заблокировали: {blocked}\n"
        f"Ошибок: {failed}"
    )
    final_buttons = [
        [("📊 Статистика рассылок", "broadcast_stats")],
        [("Назад в меню", "menu_admin")],
    ]
    await call.message.answer(
        report,
        parse_mode="HTML",
        reply_markup=await get_keyboard(final_buttons),
    )
    logger.info(
        f"Broadcast #{bid} done: sent={sent} blocked={blocked} failed={failed} total={total}"
    )


@dp.callback_query_handler(Text("broadcast_cancel"), state="*")
async def broadcast_cancel(call: types.CallbackQuery):
    await call.answer()
    admin_id = call.from_user.id

    bid = await su.get_data_from_state(admin_id, "broadcast_id")
    if bid:
        try:
            campaign_delete_broadcast(bid)
            logger.info(f"Cancelled broadcast row id={bid} by admin {admin_id}")
        except Exception as e:
            logger.error(f"Не удалось удалить broadcasts row {bid}: {e}")

    await su.reset_state_user(admin_id, clear_data=True)
    await call.message.answer(
        "Рассылка отменена.",
        reply_markup=await get_keyboard([[("Назад", "menu_admin")]]),
    )
