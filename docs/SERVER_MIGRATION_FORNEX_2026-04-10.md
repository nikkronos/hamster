# Перенос боевых сервисов (hamster / Pastuhi-стек) с Timeweb на Fornex

**Дата:** 2026-04-10  
**Связь с проектом:** боевой код на сервере исторически ведёт разработчик; в репозитории Cursor папка `Projects/PastuhiBot/` — локальная копия и документация. На VPS процессы названы **`hamster26_*`** и **`hamster93_*`** (внутренние имена у разработчика).

**Общий контекст блокировок:** с IP **Timeweb** перестал быть доступен **`api.telegram.org`** (таймауты / `No route to host`). С **Fornex** доступ к Telegram API сохранился. Полный обзор инцидента: `Main_docs/TELEGRAM_MIGRATION_TIMWEB_FORNEX_2026-04-10.md`.

---

## Что перенесли

| systemd unit | Назначение | Каталог на Fornex | Интерпретатор в venv |
|----------------|------------|-------------------|----------------------|
| `hamster26_bot.service` | бот (aiogram) | `/home/hamster26/bot/` | Python **3.10** (venv из архива Timeweb) |
| `hamster26_userbot.service` | юзербот (Pyrogram) | `/home/hamster26/userbot/` | Python **3.12** (venv пересобран на Fornex) |
| `hamster93_bot.service` | бот | `/home/hamster93_bot/` | Python **3.10** (venv из архива) |
| `hamster93_userbot.service` | юзербот | `/home/hamster93_userbot/` | Python **3.12** |
| `hamster93_feedbackbot.service` | отдельный бот (support) | `/home/hamster93_feedbackbot/` | Python **3.12** |

Unit-файлы на Fornex: **`/etc/systemd/system/hamster*.service`** (созданы вручную; на Timeweb аналоги лежали в `/usr/lib/systemd/system/`).

---

## Timeweb (после миграции)

- Все пять сервисов: **`systemctl disable --now`** — автозапуска нет, процессы не крутятся.
- Каталоги `/home/hamster*` могут остаться как резерв; **активный прод** — на Fornex.

---

## Fornex: хост и перенос данных

- VPS: **284854.fornex.cloud** (в работе использовался SSH на **185.21.8.91** — зафиксировать актуальный IP в своей панели).
- Перенос: архив **`/root/hamster-all.tar.gz`** (с Timeweb: `tar czf` из `/home` по каталогам `hamster26`, `hamster93_bot`, `hamster93_userbot`, `hamster93_feedbackbot`), распаковка в **`/home`** на Fornex.

---

## Python и виртуальные окружения

### Боты (`hamster26/bot`, `hamster93_bot`)

- В архиве venv заточен под **Python 3.10**: симлинки `venv/bin/python3.10` → **`/usr/bin/python3.10`**.
- На Ubuntu 24.04 пакета `python3.11` в базовых репозиториях не оказалось; **3.10** поставили через **deadsnakes** (`ppa:deadsnakes/ppa`, пакеты `python3.10`, `python3.10-venv`, при необходимости `python3.10-distutils`).
- Пересборка `venv` из `requirements.txt` под **Python 3.12** для этих ботов **ломалась** на сборке старых `aiohttp==3.8.4` / `yarl` / `frozenlist` — поэтому для **bot** оставили **оригинальный venv из архива** + системный **3.10**.

### Юзерботы и feedback

- venv пересоздавались: `python3 -m venv venv` (системный **3.12**), `pip install -r requirements.txt`.
- В **`requirements.txt` юзерботов не было `Pyrogram`**, хотя код импортирует `pyrogram` — после пересборки venv добавляли вручную:

  ```bash
  ./venv/bin/pip install 'Pyrogram==2.0.106'
  ./venv/bin/pip install tgcrypto
  ```

- **Рекомендация для репозитория разработчика:** добавить в `requirements.txt` юзербота строки `Pyrogram==2.0.106` и при желании `tgcrypto`, чтобы деплой не ломался.

---

## SQLite-сессии Pyrogram (`*.session`)

После обновления Pyrogram до **2.0.106** при старте возникла ошибка:

`sqlite3.OperationalError: table peers has no column named username`

Файлы сессий:

- `/home/hamster26/userbot/hamster.session`
- `/home/hamster93_userbot/hamster.session`

Исправление (с остановленными сервисами):

```bash
apt-get install -y sqlite3   # если нет CLI
sqlite3 /home/.../hamster.session "ALTER TABLE peers ADD COLUMN username TEXT;"
```

Перед этим полезно: `PRAGMA table_info(peers);` — убедиться, что колонки `username` не было.

---

## Полезные команды на Fornex

```bash
systemctl status hamster26_bot.service hamster26_userbot.service \
  hamster93_bot.service hamster93_userbot.service hamster93_feedbackbot.service --no-pager -l

journalctl -u hamster26_userbot.service -u hamster93_userbot.service -n 80 --no-pager
```

---

## Рекомендации на будущее

1. Вынести в код/репозиторий актуальные **`requirements.txt`** для всех пяти приложений (включая Pyrogram для userbot).
2. Зафиксировать в одном месте **версии Python** по каждому сервису или унифицировать (например всё на 3.10 или всё на 3.12 с обновлёнными пинами зависимостей).
3. Не хранить долгосрочно **два «прода»** на Timeweb и Fornex с одними и теми же токенами/сессиями — после переноса Timeweb держать выключенным.
4. В логах возможны **ID каналов и названия** — не публиковать сырые журналы публично.

---

## Смежные файлы

- Краткая выжимка для разработчика: `Projects/PastuhiBot/DEV_HANDOFF_FORNEX_2026-04-10.md`
- Общий отчёт по xxx / VPN / блокировке Timeweb: `Main_docs/TELEGRAM_MIGRATION_TIMWEB_FORNEX_2026-04-10.md`
