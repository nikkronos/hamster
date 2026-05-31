# Инструкция для следующего агента

## Быстрый старт

1. **Прочитай правила работы:**
   - Корневой `CLAUDE.md` монорепо + `Main_docs/PROFILE.md` — кто владелец, принципы.

2. **Изучи проект:**
   - `ROADMAP_PASTUHIBOT.md` — что в планах
   - `DONE_LIST_PASTUHIBOT.md` — что уже сделано
   - `SESSION_SUMMARY_2026-05-23.md` — последняя крупная сессия (маркетинговая кампания)

3. **Прочитай базу знаний:**
   - `docs/agent-onboarding.md` — начни отсюда
   - `docs/architecture.md` — архитектура
   - `docs/business-rules.md` — бизнес-правила
   - `docs/database.md` — структура БД
   - `docs/patterns.md` — правила кода
   - `docs/security.md` — безопасность
   - `docs/SERVER_MIGRATION_FORNEX_2026-04-10.md` — перенос на Fornex (актуальный сервер)

## Важные правила

### ⚠️ КРИТИЧЕСКИ ВАЖНО:

1. **Репозиторий:** проект живёт в отдельном репо **`nikkronos/hamster`** (PUBLIC), вынесен из монорепо `AI_Projects`.
2. **НИКОГДА не коммить секреты.** `.env`, `*.sqlite`, `*.session`, `exports/`, `*.csv` — в `.gitignore`. Репо публичный: токены/PII/сессии юзербота туда попасть не должны. `data/config.py` безопасен — читает всё из env.
3. **Перед изменением функции проверяй все связанные обработчики.**
4. **Все кнопки в меню должны иметь обработчики**, проверяй навигацию между меню.
5. **Не применяй изменения на боевом сервере без тестирования.** Боты — живой прод.

### Работа с кодом:

- Используй `validators.py` для валидации входных данных
- Логируй важные операции через `logger`
- Обрабатывай ошибки через `try-except`
- Только параметризованные SQL-запросы (никогда f-строки!)

## Сервер (Fornex)

- **Хост:** `284854.fornex.cloud` — **IP 185.21.8.91**, пользователь `root`
- **SSH:** `ssh fornex` (алиас, ключ `~/.ssh/id_ed25519_fornex`)
- **Архитектура:** два продукта на одном хосте.

| systemd unit | Назначение | Каталог |
|---|---|---|
| `hamster93_bot.service` | бот (старая база, ~682 юзера) | `/home/hamster93_bot/` |
| `hamster93_userbot.service` | юзербот (Pyrogram) | `/home/hamster93_userbot/` |
| `hamster93_feedbackbot.service` | support-бот | `/home/hamster93_feedbackbot/` |
| `hamster26_bot.service` | бот «Пастухи 2.0» (актуальный) | `/home/hamster26/bot/` |
| `hamster26_userbot.service` | юзербот (Pyrogram) | `/home/hamster26/userbot/` |

- Боты — Python **3.10** (venv из архива), юзерботы — Python **3.12**.
- Campaign-данные (`broadcasts`, `broadcast_clicks`) живут в БД **hamster26**: `/home/hamster26/bot/database/database.sqlite`.

**Обновление на сервере (SCP напрямую, не git pull):**
```powershell
# пример: один файл бота hamster93
scp "C:\Users\krono\OneDrive\Рабочий стол\AI_Projects\Projects\Non actual\PastuhiBot\handlers\admins\broadcast.py" fornex:/home/hamster93_bot/handlers/admins/
```
```bash
# на сервере
systemctl restart hamster93_bot.service
journalctl -u hamster93_bot.service -f
```

> ⚠️ Локальная копия и сервер могут расходиться (работа исторически велась напрямую на сервере). Перед деплоем — сверяй файлы.

## Полезные команды

```bash
# статус всех сервисов
systemctl status hamster93_bot hamster26_bot hamster93_userbot hamster26_userbot hamster93_feedbackbot --no-pager -l

# экспорт пользователей (на сервере, в каталоге бота)
cd /home/hamster93_bot && source venv/bin/activate && python export_users_simple.py
```

## Что уже сделано / в планах

- Выполненное: `DONE_LIST_PASTUHIBOT.md`
- Планы: `ROADMAP_PASTUHIBOT.md`

---

**Удачи!** 🚀
