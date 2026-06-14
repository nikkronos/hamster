"""
Выгрузка постов отслеживаемых каналов («пастухов») за период в один .md-файл.

Назначение: дайджест. Файл отдаётся в LLM (Grok) для саммари недели —
«как пастухи готовились к данным» / «трейды недели».

Запуск на сервере Fornex в окружении юзербота hamster26:

    cd /home/hamster26/userbot
    venv/bin/python /path/to/export_channel_posts.py --days 7

Безопасность (важно — это живой прод):
* НЕ трогает работающий юзербот: скрипт работает с КОПИЕЙ session-файла
  (консистентный sqlite-backup), под отдельным именем клиента и в отдельном
  workdir. Параллельное подключение с тем же auth_key безопасно — у каждого
  соединения свой session_id (так же работает Telegram на нескольких устройствах).
* Read-only: только get_chat / get_chat_history по Telegram и SELECT по БД.
* Секретов в коде нет: api_id/api_hash берутся из самой session-копии.

По умолчанию каналы-чаты (GROUP/SUPERGROUP) исключаются — в дайджест идут
только сигнальные каналы. Чаты можно вернуть флагом --include-chats.
"""
import argparse
import asyncio
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, RPCError

DEFAULT_DB = "/home/hamster26/bot/database/database.sqlite"
DEFAULT_SESSION = "/home/hamster26/userbot/hamster.session"
DEFAULT_OUT_DIR = "/home/hamster26/userbot/_digest"

# Источники — это ре-броды агрегатора (VipPirates): даже чаты приходят как
# ChatType.CHANNEL, поэтому чаты отсекаем по маркерам в названии (stored + live),
# а ChatType GROUP/SUPERGROUP оставляем как дополнительную страховку.
CHAT_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
CHAT_TITLE_MARKERS = ("чат", "chat", "адм", "admin")


def is_chat_channel(chat_type, *titles):
    blob = " ".join(t for t in titles if t).lower()
    if any(m in blob for m in CHAT_TITLE_MARKERS):
        return True
    return chat_type in CHAT_TYPES


def has_author_prefix(text):
    """Первая строка вида «Имя:» (реплика участника). Признак чат-ленты."""
    if not text:
        return False
    first = text.split("\n", 1)[0].strip()
    return 1 <= len(first) <= 35 and first.endswith(":")


def feed_density(posts):
    """Доля постов с префиксом-автором, %. 100% ≈ чат-лента, не сигнальный канал."""
    if not posts:
        return 0
    n = sum(1 for p in posts if has_author_prefix(p["text"]))
    return round(100 * n / len(posts))


def parse_args():
    p = argparse.ArgumentParser(description="Выгрузка постов каналов за период в .md")
    p.add_argument("--days", type=int, default=7, help="за сколько последних суток (UTC), по умолчанию 7")
    p.add_argument("--db", default=DEFAULT_DB, help="путь к БД бота с tracked_channels")
    p.add_argument("--session-src", default=DEFAULT_SESSION, help="путь к живой session юзербота (копируется, не трогается)")
    p.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="куда сохранить .md и рабочую копию сессии")
    p.add_argument("--include-chats", action="store_true", help="включить каналы-чаты (по названию чат/адм)")
    p.add_argument("--max-msgs", type=int, default=600, help="лимит постов на канал (предохранитель)")
    p.add_argument("--limit-channels", type=int, default=0, help="обработать только первые N каналов (для smoke-теста)")
    p.add_argument("--feed-threshold", type=int, default=60,
                   help="порог плотности реплик (%%), выше — канал считается чат-лентой и исключается")
    p.add_argument("--keep-feeds", action="store_true", help="не исключать чат-ленты по плотности реплик")
    p.add_argument("--exclude-ids", default="", help="channel_id через запятую — исключить вручную")
    return p.parse_args()


def load_tracked_channels(db_path):
    """Список (channel_id, title, forward_channel_id) из БД бота."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        cur.execute("SELECT channel_id, title, forward_channel_id FROM tracked_channels ORDER BY id")
        return cur.fetchall()
    finally:
        con.close()


def copy_session(session_src, out_dir):
    """Консистентная копия session-файла (sqlite backup), чтобы не лочить живой файл."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    copy_path = out / "hamster_digest.session"
    if copy_path.exists():
        copy_path.unlink()
    src = sqlite3.connect(f"file:{session_src}?mode=ro", uri=True)
    dst = sqlite3.connect(str(copy_path))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return copy_path


def media_tag(msg):
    """Короткий маркер медиа для текстового дайджеста."""
    for attr, tag in (
        ("photo", "фото"),
        ("video", "видео"),
        ("animation", "gif"),
        ("document", "документ"),
        ("audio", "аудио"),
        ("voice", "голосовое"),
        ("video_note", "кружок"),
        ("sticker", "стикер"),
        ("poll", "опрос"),
    ):
        if getattr(msg, attr, None):
            return tag
    return None


def msg_text(msg):
    return msg.text or msg.caption or ""


def to_naive_utc(dt):
    """Pyrogram 2.0.x отдаёт naive-UTC; на всякий случай приводим aware->naive UTC."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def resolve_chat(app, channel_id):
    """Возвращает (chat_type, live_title, error). Дёшево — нужно до выкачки истории."""
    try:
        chat = await app.get_chat(channel_id)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        chat = await app.get_chat(channel_id)
        return chat.type, chat.title, None
    except RPCError as e:
        return None, None, f"get_chat: {e}"
    return chat.type, chat.title, None


async def fetch_history(app, channel_id, since, until, max_msgs):
    """Посты канала за период. Возвращает (posts oldest->newest, error)."""
    posts = []
    count = 0
    try:
        async for msg in app.get_chat_history(channel_id):
            mdate = to_naive_utc(msg.date)
            if mdate is None:
                continue
            if mdate < since:
                break  # история идёт от новых к старым — дальше только старее
            if mdate > until:
                continue
            if getattr(msg, "service", None):
                continue
            text = msg_text(msg).strip()
            tag = media_tag(msg)
            if not text and not tag:
                continue
            posts.append({"date": mdate, "id": msg.id, "text": text, "media": tag})
            count += 1
            if count >= max_msgs:
                break
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except RPCError as e:
        posts.reverse()
        return posts, f"get_chat_history: {e}"

    posts.reverse()  # oldest -> newest
    return posts, None


def render_markdown(meta, channels):
    """channels: list of dicts с ключами title, channel_id, type, posts, error, skip_reason, density."""
    lines = []
    lines.append(f"# Дайджест постов каналов")
    lines.append("")
    lines.append(f"- Период (UTC): **{meta['since']:%Y-%m-%d %H:%M}** — **{meta['until']:%Y-%m-%d %H:%M}** (последние {meta['days']} сут.)")
    lines.append(f"- Сформировано: {meta['generated']:%Y-%m-%d %H:%M} UTC")
    included = [c for c in channels if not c["skip_reason"]]  # сигнальные каналы (рендерим всегда)
    excluded = [c for c in channels if c["skip_reason"]]
    errored = [c for c in included if c["error"]]
    total_posts = sum(len(c["posts"]) for c in included)
    lines.append(f"- Каналов в дайджесте: **{len(included)}**, постов всего: **{total_posts}**")
    if excluded:
        lines.append(f"- Исключено ({len(excluded)}): " + ", ".join(f"{c['title']} [{c['skip_reason']}]" for c in excluded))
    if errored:
        lines.append(f"- С ошибкой доступа ({len(errored)}): " + ", ".join(f"{c['title']} [{c['error']}]" for c in errored))
    lines.append("")
    lines.append("---")
    lines.append("")

    for c in included:
        lines.append(f"## {c['title']}")
        if c["error"]:
            lines.append("")
            lines.append(f"_(ошибка доступа: {c['error']})_")
            lines.append("")
        if not c["posts"]:
            lines.append("")
            lines.append("_(за период постов нет)_")
            lines.append("")
            continue
        lines.append("")
        for p in c["posts"]:
            stamp = p["date"].strftime("%Y-%m-%d %H:%M")
            media = f" [{p['media']}]" if p["media"] else ""
            header = f"**[{stamp}]**{media}"
            lines.append(header)
            if p["text"]:
                lines.append("")
                lines.append(p["text"])
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


async def run():
    args = parse_args()
    until = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC — как msg.date в Pyrogram 2.0.x
    since = until - timedelta(days=args.days)

    exclude_ids = {int(x) for x in args.exclude_ids.split(",") if x.strip()}

    tracked = load_tracked_channels(args.db)
    if args.limit_channels:
        tracked = tracked[: args.limit_channels]
    print(f"Каналов в БД к обработке: {len(tracked)}; период {since:%Y-%m-%d} — {until:%Y-%m-%d} UTC")

    copy_path = copy_session(args.session_src, args.out_dir)
    print(f"Рабочая копия сессии: {copy_path}")

    name = copy_path.stem  # hamster_digest
    workdir = str(copy_path.parent)

    channels = []
    async with Client(name, workdir=workdir) as app:
        for channel_id, title, _forward in tracked:
            entry = {"title": title, "channel_id": channel_id, "type": None,
                     "posts": [], "error": None, "skip_reason": None, "density": None}
            try:
                chat_type, live_title, error = await resolve_chat(app, channel_id)
                entry["type"] = chat_type
                entry["title"] = live_title or title
                if channel_id in exclude_ids:
                    entry["skip_reason"] = "вручную"
                    entry["error"] = error
                    print(f"  skip (вручную): {entry['title']}")
                # классификация чат/сигнал по названию (stored + live), решаем ДО выкачки
                elif is_chat_channel(chat_type, title, live_title) and not args.include_chats:
                    entry["skip_reason"] = "чат (название)"
                    entry["error"] = error  # сохраним причину, если канал был недоступен
                    print(f"  skip (чат): {entry['title']}")
                elif error:
                    entry["error"] = error
                    print(f"  ERROR resolve: {title} ({channel_id}): {error}")
                else:
                    posts, herr = await fetch_history(app, channel_id, since, until, args.max_msgs)
                    entry["posts"] = posts
                    entry["error"] = herr
                    dens = feed_density(posts)
                    entry["density"] = dens
                    # авто-исключение чат-лент по плотности реплик (после выкачки)
                    if dens >= args.feed_threshold and not args.keep_feeds:
                        entry["skip_reason"] = f"чат-лента {dens}%"
                        print(f"  skip (чат-лента {dens}%): {entry['title']} — {len(posts)} реплик отброшено")
                    else:
                        print(f"  ok: {entry['title']} — {len(posts)} постов (реплик {dens}%)"
                              + (f" [{herr}]" if herr else ""))
            except Exception as e:
                entry["error"] = str(e)
                print(f"  ERROR: {title} ({channel_id}): {e}")
            channels.append(entry)
            await asyncio.sleep(0.3)

    meta = {"since": since, "until": until, "days": args.days,
            "generated": datetime.now(timezone.utc).replace(tzinfo=None)}
    md = render_markdown(meta, channels)

    fname = f"digest_{since:%Y-%m-%d}_to_{until:%Y-%m-%d}.md"
    out_path = Path(args.out_dir) / fname
    out_path.write_text(md, encoding="utf-8")
    total = sum(len(c["posts"]) for c in channels if not c["skip_reason"])
    print(f"\nГотово: {out_path}")
    print(f"Постов в дайджесте: {total}; размер файла: {out_path.stat().st_size} байт")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
