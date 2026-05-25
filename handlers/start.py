"""
hamster26: handler /start с поддержкой deep link.

Изменения относительно оригинала:
- Поведение БЕЗ параметра — идентичное оригиналу.
- При /start с параметром "p<broadcast_id>" — обрабатываем как клик по рассылке:
  логируем клик, применяем промокод к state, показываем CTA на оплату.
- При ЛЮБОЙ ошибке в обработке deep link — graceful fallback в обычный flow.
"""
import datetime
import logging

from aiogram import types
from aiogram.dispatcher.filters import Text

import keyboards
from database.getters import get_data
from database.setters import add_new_data
from keyboards.keyboards import get_keyboard
from loader import dp
from utils.states_users import reset_state_user, save_data_state

logger = logging.getLogger(__name__)

DISCLAIMER_TEXT = (
    "Важный дисклеймер: здесь нет индивидуальных инвестиционных рекомендаций (ИИР), "
    "всю информацию необходимо использовать с личной ответственностью.\n"
    "\n"
    "Для продолжения нажмите кнопку ниже."
)

DISCOUNT_PRICE = 1000  # Фиксированная цена для промокода рассылки


async def _register_user_if_new(from_user, msg_date):
    """Регистрирует пользователя в users если его там нет"""
    user_id = from_user.id
    user_data = await get_data("users", user_id=user_id)
    if not user_data:
        user_data = (
            user_id,
            from_user.first_name,
            from_user.username,
            msg_date,
        )
        await add_new_data("users", user_data, start_index=0)


async def _send_regular_start(user_id):
    """Стандартное стартовое сообщение (как в оригинале)"""
    await dp.bot.send_message(
        user_id,
        DISCLAIMER_TEXT,
        disable_web_page_preview=True,
        reply_markup=await keyboards.users.start(user_id),
    )


@dp.message_handler(commands="start", state="*")
async def start_command(message: types.Message):
    """Обработка /start. Если есть параметр p<id> — пробуем как deep link рассылки."""
    user_id = message.from_user.id
    args = (message.get_args() or "").strip()

    await reset_state_user(user_id, clear_data=True)
    await _register_user_if_new(message.from_user, message.date)

    # Deep link с промокодом: /start p<broadcast_id>
    if args.startswith("p") and args[1:].isdigit():
        try:
            broadcast_id = int(args[1:])
            handled = await _handle_deep_link_promo(message, broadcast_id)
            if handled:
                return
        except Exception as e:
            logger.exception(
                f"Deep link handler упал для user_id={user_id} args={args}: {e}"
            )
            # Намеренно проваливаемся в обычный flow ниже

    await _send_regular_start(user_id)


@dp.callback_query_handler(Text("start"), state="*")
async def start_callback(call: types.CallbackQuery):
    """Возврат к стартовому меню по кнопке (без deep link)"""
    user_id = call.from_user.id
    await reset_state_user(user_id, clear_data=True)
    msg_date = call.message.date if call.message else datetime.datetime.now()
    await _register_user_if_new(call.from_user, msg_date)
    await _send_regular_start(user_id)
    await call.answer()


async def _handle_deep_link_promo(message, broadcast_id):
    """
    Обрабатывает клик по кнопке рассылки. Возвращает True если deep link
    действительно обработан (рассылка найдена, промокод применён или показано
    финальное сообщение). False — если надо упасть в обычный /start flow.
    """
    user_id = message.from_user.id

    # 1) Логируем клик ВСЕГДА — даже если дальше что-то пойдёт не так
    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        await add_new_data("broadcast_clicks", (broadcast_id, user_id, now_str))
    except Exception as e:
        logger.error(f"Не удалось залогировать клик broadcast={broadcast_id} user={user_id}: {e}")

    # 2) Достаём данные рассылки
    broadcast = await get_data("broadcasts", id=broadcast_id)
    if not broadcast:
        logger.warning(f"broadcasts.id={broadcast_id} не найден — fallback")
        return False

    promo_code = broadcast.get("promocode")
    if not promo_code:
        # Рассылка без промокода (только tracking) — обычный start, но клик уже залогирован
        return False

    # 3) Проверяем промокод
    promo_data = await get_data("promocodes", promocode=promo_code, fetch="all")
    if not promo_data:
        logger.warning(f"Промокод {promo_code} не найден в БД")
        return False

    promo = promo_data[-1]
    try:
        expiration = datetime.datetime.strptime(
            promo["expiration"], "%Y-%m-%d %H:%M:%S.%f"
        )
    except Exception as e:
        logger.error(f"Не распарсить expiration '{promo['expiration']}': {e}")
        return False

    if expiration < datetime.datetime.now():
        await dp.bot.send_message(
            user_id,
            "К сожалению, эта акция уже закончилась 😔\n\n"
            "Ты всё равно можешь оформить подписку по обычной цене.",
            reply_markup=await keyboards.users.start(user_id),
        )
        return True

    # 4) Применяем промокод к state пользователя (через FSM data)
    await save_data_state(user_id, amount=DISCOUNT_PRICE)
    await save_data_state(user_id, activate_promocode=promo_code)
    await save_data_state(user_id, months=1)

    # 5) Смотрим — есть ли активная подписка
    sub = await get_data("user_subscriptions", user_id=user_id)
    sub_end_str = None
    if sub:
        try:
            sub_end_dt = datetime.datetime.strptime(
                sub["datetime_end_subscribe"], "%Y-%m-%d %H:%M:%S.%f"
            )
            if sub_end_dt > datetime.datetime.now():
                sub_end_str = sub_end_dt.strftime("%d.%m.%Y")
        except Exception:
            pass  # парсинг не критичен

    if sub_end_str:
        text = (
            f"🎉 <b>Скидка активирована!</b>\n\n"
            f"У тебя сейчас активная подписка до <b>{sub_end_str}</b>.\n\n"
            f"Если возьмёшь ещё месяц со скидкой — 30 дней добавятся к текущей подписке.\n\n"
            f"💰 Цена: <b>{DISCOUNT_PRICE}₽</b> вместо 1500₽\n"
            f"⏰ Акция действует до 31 мая 2026."
        )
    else:
        text = (
            f"🎉 <b>Твоя индивидуальная скидка активирована!</b>\n\n"
            f"Месяц подписки за <b>{DISCOUNT_PRICE}₽</b> вместо 1500₽.\n\n"
            f"⏰ Акция действует до 31 мая 2026."
        )

    buttons = [
        [(f"💳 Оплатить {DISCOUNT_PRICE}₽", "req_scrn_pay_1")],
        [("Назад", "start")],
    ]

    await dp.bot.send_message(
        user_id,
        text,
        parse_mode="HTML",
        reply_markup=await get_keyboard(buttons),
    )
    return True
