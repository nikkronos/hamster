# Развертывание и обновление на сервере

## Текущее окружение

- **Сервер:** Fornex — `284854.fornex.cloud` (Ubuntu 24.04)
- **IP:** 185.21.8.91
- **Пользователь:** root (SSH-алиас `ssh fornex`, ключ `~/.ssh/id_ed25519_fornex`)
- **Расположение бота:** `/home/hamster93_bot/` (hamster26 — `/home/hamster26/bot/`)
- **База данных:** SQLite (`database/database.sqlite`)

> Ранее жил на Timeweb (81.200.146.32) — перенесён на Fornex 2026-04-10 из-за блокировки Telegram API с IP Timeweb. См. `docs/SERVER_MIGRATION_FORNEX_2026-04-10.md`.

## Процесс обновления на сервере

### Важно: 
- **Код коммитим в репозиторий `nikkronos/hamster`** (PUBLIC). Деплой на сервер — вручную через SCP, не через git pull.
- Секреты (`.env`, `*.sqlite`, `*.session`) в репо не попадают (`.gitignore`).
- Боевой бот продолжает работать во время подготовки обновлений

### Шаг 1: Подготовка обновлений локально

1. Убедитесь, что все изменения протестированы локально
2. Создайте архив с обновленными файлами:

```powershell
# В PowerShell на вашем компьютере
cd "C:\Users\krono\OneDrive\Рабочий стол\Cursor_Projects\Projects\Non actual\PastuhiBot"

# Создать архив (исключая ненужные файлы)
tar -czf update_backup.tar.gz --exclude='venv' --exclude='__pycache__' --exclude='loggs' --exclude='*.pyc' --exclude='*.session*' --exclude='database.sqlite' .
```

### Шаг 2: Подключение к серверу

```powershell
# В PowerShell
ssh fornex
# Введите пароль
```

### Шаг 3: Создание бэкапа на сервере

```bash
# На сервере
cd /home/hamster93_bot

# Создать бэкап текущей версии
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz --exclude='venv' --exclude='__pycache__' --exclude='loggs' --exclude='*.pyc' --exclude='*.session*' .

# Создать бэкап базы данных
cp database/database.sqlite database/database.sqlite.backup_$(date +%Y%m%d_%H%M%S)
```

### Шаг 4: Остановка бота

```bash
# Остановить systemd сервис
systemctl stop hamster93_bot.service

# Проверить, что бот остановлен
systemctl status hamster93_bot.service
```

### Шаг 5: Копирование обновлений на сервер

**Вариант A: Через SCP (из PowerShell на вашем компьютере)**

```powershell
# Скачать архив на сервер
scp "C:\Users\krono\OneDrive\Рабочий стол\Cursor_Projects\Projects\Non actual\PastuhiBot\update_backup.tar.gz" fornex:/tmp/
```

**Вариант B: Через WinSCP (графический интерфейс)**

1. Откройте WinSCP
2. Подключитесь к серверу (fornex)
3. Перетащите файл `update_backup.tar.gz` в `/tmp/` на сервере

### Шаг 6: Применение обновлений на сервере

```bash
# На сервере
cd /home/hamster93_bot

# Распаковать обновления во временную папку
mkdir -p /tmp/hamster93_update
tar -xzf /tmp/update_backup.tar.gz -C /tmp/hamster93_update

# Скопировать обновленные файлы (кроме критических)
# ВАЖНО: НЕ перезаписываем database.sqlite и .env!
cp -r /tmp/hamster93_update/* ./
cp -r /tmp/hamster93_update/.* . 2>/dev/null || true

# Восстановить критичные файлы (если нужно)
# cp database/database.sqlite.backup_* database/database.sqlite  # Только если нужно откатиться
# .env файл не трогаем - он уже настроен на сервере

# Очистить временные файлы
rm -rf /tmp/hamster93_update
rm /tmp/update_backup.tar.gz
```

### Шаг 7: Обновление зависимостей (если нужно)

```bash
# Если изменился requirements.txt
cd /home/hamster93_bot
source venv/bin/activate
pip install -r requirements.txt
```

### Шаг 8: Запуск бота

```bash
# Запустить systemd сервис
systemctl start hamster93_bot.service

# Проверить статус
systemctl status hamster93_bot.service

# Посмотреть логи
journalctl -u hamster93_bot.service -f
```

### Шаг 9: Проверка работы

1. Проверьте логи на наличие ошибок
2. Протестируйте основные функции бота
3. Если что-то не работает - откатите изменения (см. ниже)

## Откат изменений (если что-то пошло не так)

```bash
# На сервере
cd /home/hamster93_bot

# Остановить бота
systemctl stop hamster93_bot.service

# Восстановить из бэкапа
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz

# Восстановить базу данных (если нужно)
cp database/database.sqlite.backup_YYYYMMDD_HHMMSS database/database.sqlite

# Запустить бота
systemctl start hamster93_bot.service
```

## Быстрая команда для обновления (после подготовки архива)

Если вы уже подготовили архив и скопировали его на сервер:

```bash
# На сервере - выполнить одной командой
cd /home/hamster93_bot && \
systemctl stop hamster93_bot.service && \
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz --exclude='venv' --exclude='__pycache__' --exclude='loggs' --exclude='*.pyc' --exclude='*.session*' . && \
cp database/database.sqlite database/database.sqlite.backup_$(date +%Y%m%d_%H%M%S) && \
mkdir -p /tmp/hamster93_update && \
tar -xzf /tmp/update_backup.tar.gz -C /tmp/hamster93_update && \
cp -r /tmp/hamster93_update/* ./ && \
rm -rf /tmp/hamster93_update && \
systemctl start hamster93_bot.service && \
systemctl status hamster93_bot.service
```

## Важные замечания

1. **Всегда создавайте бэкап** перед обновлением
2. **Не перезаписывайте** `database.sqlite` и `.env` файлы
3. **Проверяйте логи** после обновления
4. **Тестируйте** на тестовом боте перед применением на боевом
5. **Храните бэкапы** минимум неделю

## Мониторинг

- Логи бота: `journalctl -u hamster93_bot.service -f`
- Логи в файле: `tail -f /home/hamster93_bot/loggs/bot.log`
- Статус сервиса: `systemctl status hamster93_bot.service`

## Экспорт пользователей

Для экспорта пользователей используйте скрипт:

```bash
# На сервере
cd /home/hamster93_bot
source venv/bin/activate
python scripts/export_users.py
```

Файлы будут сохранены в папке `exports/`:
- `all_users_YYYYMMDD_HHMMSS.csv` - все пользователи
- `active_users_YYYYMMDD_HHMMSS.csv` - только активные

Затем скачайте файлы через SCP или WinSCP.


























