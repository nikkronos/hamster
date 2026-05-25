# Для разработчика: что изменилось 2026-04-10

Кратко, чтобы было понятно без доступа к переписке.

## Зачем

С **Timeweb** перестал открываться **`api.telegram.org`** (сетевая блокировка/фильтрация). Все Telegram-боты и юзерботы на этом IP перестали работать. **Прод перенесён на Fornex.**

## Что касается твоего стека (hamster26 / hamster93)

Пять процессов теперь крутятся на **VPS Fornex** (не на Timeweb):

| Unit | Папка |
|------|--------|
| `hamster26_bot.service` | `/home/hamster26/bot/` |
| `hamster26_userbot.service` | `/home/hamster26/userbot/` |
| `hamster93_bot.service` | `/home/hamster93_bot/` |
| `hamster93_userbot.service` | `/home/hamster93_userbot/` |
| `hamster93_feedbackbot.service` | `/home/hamster93_feedbackbot/` |

На **Timeweb** эти же unit’ы **отключены** (`disable` + `stop`) — двойного запуска быть не должно.

## Технические нюансы (важно для следующего деплоя)

1. **Боты** (`…/bot/` у 26 и 93): venv из бэкапа заточен под **Python 3.10** (симлинк на `/usr/bin/python3.10`). На новом сервере нужен установленный **python3.10** (у нас — из deadsnakes). Пересборка этого venv под 3.12 без обновления зависимостей **не взлетела** (старый aiohttp/yarl).

2. **Юзерботы**: venv пересобран под **Python 3.12**. В **`requirements.txt` юзербота не было `Pyrogram`**, из-за этого после чистого `pip install -r` падало с `No module named pyrogram`. На сервере поставили: `Pyrogram==2.0.106` и `tgcrypto`. **Просьба:** добавить Pyrogram (и при желании tgcrypto) в `requirements.txt` юзербота в твоём репозитории.

3. **Файлы `hamster.session`**: после Pyrogram 2.0.106 понадобилось одно изменение SQLite:  
   `ALTER TABLE peers ADD COLUMN username TEXT;`  
   (иначе `OperationalError` при старте). Подробно — в `docs/SERVER_MIGRATION_FORNEX_2026-04-10.md`.

## Где полная документация

`Projects/PastuhiBot/docs/SERVER_MIGRATION_FORNEX_2026-04-10.md`

## Контекст по другим проектам на том же Fornex

На этом же хосте уже работают перенесённые ранее **Копия иксуюемся** (`/opt/kopiya-iksuyemsya`) и **VPN Telegram-бот** (`/opt/vpnservice`). Общая статья: `Main_docs/TELEGRAM_MIGRATION_TIMWEB_FORNEX_2026-04-10.md`.

---

Если нужны актуальные IP, ключи доступа к Fornex или правки unit-файлов — это у владельца инфраструктуры; в этом файле только согласованное техническое состояние после миграции.
