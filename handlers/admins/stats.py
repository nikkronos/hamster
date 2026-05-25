"""
Phase 4: Статистика рассылок.

Читает данные из единой БД hamster26 (broadcasts + broadcast_clicks + payments).
Работает идентично в обоих ботах (hamster93 и hamster26).
"""
import datetime
import logging
import sqlite3

from aiogram import types
from aiogram.dispatcher.filters import Text

from data import config
from keyboards.keyboards import get_keyboard
from loader import dp

logger = logging.getLogger(__name__)

CAMPAIGN_DB = "/home/hamster26/bot/database/database.sqlite"
PAGE_SIZE = 10


def _conn():
    return sqlite3.connect(CAMPAIGN_DB, timeout=10.0)


def get_total_count():
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM broadcasts")
        return cur.fetchone()[0]


def get_stats_page(limit, offset):
    """Возвращает список dict-ов: рассылки + клики + конверсия"""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                b.id, b.from_bot, b.audience, b.promocode,
                b.has_photo, b.preview,
                b.recipients, b.delivered, b.blocked, b.failed,
                b.created_at, b.completed_at,
                (SELECT COUNT(*) FROM broadcast_clicks WHERE broadcast_id = b.id) as total_clicks,
                (SELECT COUNT(DISTINCT user_id) FROM broadcast_clicks WHERE broadcast_id = b.id) as uniq_clicks
            FROM broadcasts b
            ORDER BY b.id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cur.fetchall()

        result = []
        for r in rows:
            (bid, from_bot, audience, promo, has_photo, preview,
             recipients, delivered, blocked, failed,
             created_at, completed_at, total_clicks, uniq_clicks) = r

            # Конверсия: те, кто кликнул на эту рассылку И сделал оплату с этим промокодом И is_paid=1
            paid_users = 0
            revenue = 0
            if promo:
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT p.user_id), COALESCE(SUM(CAST(p.amount AS INTEGER)), 0)
                    FROM payments p
                    WHERE p.is_paid = 1
                      AND p.promocode = ?
                      AND p.user_id IN (
                          SELECT DISTINCT user_id FROM broadcast_clicks WHERE broadcast_id = ?
                      )
                    """,
                    (promo, bid),
                )
                row = cur.fetchone()
                if row:
                    paid_users = row[0] or 0
                    revenue = row[1] or 0

            result.append({
                "id": bid,
                "from_bot": from_bot,
                "audience": audience,
                "promo": promo,
                "preview": preview or "",
                "recipients": recipients or 0,
                "delivered": delivered or 0,
                "blocked": blocked or 0,
                "failed": failed or 0,
                "created_at": created_at,
                "completed_at": completed_at,
                "total_clicks": total_clicks or 0,
                "uniq_clicks": uniq_clicks or 0,
                "paid_users": paid_users,
                "revenue": revenue,
            })
        return result


def _format_date(date_str):
    if not date_str:
        return "—"
    try:
        # Поддерживаем оба формата: с микросекундами и без
        date_clean = date_str.split(".")[0]
        dt = datetime.datetime.strptime(date_clean, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d.%m %H:%M")
    except Exception:
        return date_str[:16] if date_str else "—"


def format_broadcast(b):
    audience_label = {
        "all": "все",
        "active": "активн.",
        "inactive": "неактивн.",
    }.get(b["audience"], b["audience"] or "?")

    status_icon = "✅" if b["completed_at"] else "⏳"
    date = _format_date(b["completed_at"] or b["created_at"])
    promo_str = b["promo"] or "—"
    photo_icon = "🖼" if b.get("has_photo") else "📝"

    preview = (b["preview"] or "").replace("\n", " ")[:50]
    if len(b["preview"] or "") > 50:
        preview += "…"

    # Header
    lines = [
        f"{status_icon} <b>#{b['id']}</b> · {date} · {b['from_bot']} → {audience_label} · {photo_icon}",
    ]

    # Промокод
    if b["promo"]:
        lines.append(f"   🎁 {promo_str}")

    # Доставка
    if b["completed_at"]:
        lines.append(
            f"   📤 {b['delivered']}/{b['recipients']} · ⛔ {b['blocked']} · ❌ {b['failed']}"
        )
    elif b["recipients"]:
        lines.append(f"   ⏳ Запланировано: {b['recipients']}, не отправлено")

    # Клики и конверсия
    if b["total_clicks"] > 0 or b["promo"]:
        ctr = ""
        if b["delivered"] > 0:
            pct = round(b["uniq_clicks"] * 100 / b["delivered"], 1)
            ctr = f" ({pct}% CTR)"
        lines.append(
            f"   👆 {b['total_clicks']} клик. / {b['uniq_clicks']} уник.{ctr}"
        )
        if b["promo"]:
            conv_pct = ""
            if b["uniq_clicks"] > 0:
                pct = round(b["paid_users"] * 100 / b["uniq_clicks"], 1)
                conv_pct = f" ({pct}% конв.)"
            lines.append(
                f"   💰 {b['paid_users']} оплат{conv_pct} · {b['revenue']}₽"
            )

    # Превью
    lines.append(f"   <i>{preview}</i>")

    return "\n".join(lines)


@dp.callback_query_handler(Text("broadcast_stats"), state="*")
async def show_stats_root(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return
    await _send_stats_page(call.message, page=0)


@dp.callback_query_handler(Text(startswith="bstats_page_"), state="*")
async def show_stats_paged(call: types.CallbackQuery):
    await call.answer()
    if call.from_user.id not in config.ADMINS:
        return
    try:
        page = int(call.data.replace("bstats_page_", ""))
    except ValueError:
        page = 0
    await _send_stats_page(call.message, page=page)


async def _send_stats_page(message, page=0):
    total = get_total_count()

    if total == 0:
        await message.answer(
            "📊 <b>Статистика рассылок</b>\n\n"
            "Пока ни одной рассылки не было.\n"
            "Когда отправишь первую — здесь появятся данные.",
            parse_mode="HTML",
            reply_markup=await get_keyboard([[("Назад", "menu_admin")]]),
        )
        return

    offset = page * PAGE_SIZE
    data = get_stats_page(limit=PAGE_SIZE, offset=offset)

    if not data:
        # Перешли за границы
        await message.answer(
            "Это последняя страница.",
            reply_markup=await get_keyboard([
                [("⏮ К началу", "bstats_page_0")],
                [("Назад", "menu_admin")],
            ]),
        )
        return

    last_page = max(0, (total - 1) // PAGE_SIZE)
    header = (
        f"📊 <b>Статистика рассылок</b>\n"
        f"Всего: {total} · Страница {page + 1}/{last_page + 1}\n\n"
    )
    body = "\n\n".join(format_broadcast(b) for b in data)
    text = header + body

    # Telegram limit
    if len(text) > 4000:
        text = text[:3990] + "\n…"

    nav_row = []
    if page > 0:
        nav_row.append(("⬅ Назад", f"bstats_page_{page - 1}"))
    if page < last_page:
        nav_row.append(("Дальше ➡", f"bstats_page_{page + 1}"))

    buttons = []
    if nav_row:
        buttons.append(nav_row)
    buttons.append([("🔄 Обновить", f"bstats_page_{page}")])
    buttons.append([("Назад в меню", "menu_admin")])

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=await get_keyboard(buttons),
    )
