# Инструкция по обновлению PastuhiBot на сервере

## Быстрый старт

### 1. Подготовка обновлений (на вашем компьютере)

```powershell
# Перейти в папку проекта
cd "C:\Users\krono\OneDrive\Рабочий стол\AI_Projects\Projects\In progress\PastuhiBot"

# Создать архив с обновлениями
tar -czf update_backup.tar.gz --exclude='venv' --exclude='__pycache__' --exclude='loggs' --exclude='*.pyc' --exclude='*.session*' --exclude='database.sqlite' .
```

### 2. Копирование на сервер

```powershell
# Скопировать архив на сервер
scp update_backup.tar.gz fornex:/tmp/
```

### 3. Применение обновлений (на сервере через SSH)

```bash
# Подключиться к серверу
ssh fornex

# Выполнить обновление
cd /home/hamster93_bot
systemctl stop hamster93_bot.service
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz --exclude='venv' --exclude='__pycache__' --exclude='loggs' --exclude='*.pyc' --exclude='*.session*' .
cp database/database.sqlite database/database.sqlite.backup_$(date +%Y%m%d_%H%M%S)
mkdir -p /tmp/hamster93_update
tar -xzf /tmp/update_backup.tar.gz -C /tmp/hamster93_update
cp -r /tmp/hamster93_update/* ./
rm -rf /tmp/hamster93_update
systemctl start hamster93_bot.service
systemctl status hamster93_bot.service
```

### 4. Проверка

```bash
# Посмотреть логи
journalctl -u hamster93_bot.service -f
```

## Откат (если что-то пошло не так)

```bash
cd /home/hamster93_bot
systemctl stop hamster93_bot.service
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz
cp database/database.sqlite.backup_YYYYMMDD_HHMMSS database/database.sqlite
systemctl start hamster93_bot.service
```

## Экспорт пользователей

### Вариант 1: Скопировать скрипт на сервер

```powershell
# На вашем компьютере - скопировать скрипт на сервер
scp "C:\Users\krono\OneDrive\Рабочий стол\AI_Projects\Projects\In progress\PastuhiBot\export_users_simple.py" fornex:/home/hamster93_bot/
```

```bash
# На сервере
cd /home/hamster93_bot
source venv/bin/activate
python export_users_simple.py
```

### Вариант 2: Создать скрипт прямо на сервере

```bash
# На сервере - создать файл
nano export_users_simple.py
# Вставить содержимое файла export_users_simple.py
# Сохранить (Ctrl+O, Enter, Ctrl+X)

# Запустить
cd /home/hamster93_bot
source venv/bin/activate
python export_users_simple.py
```

Файлы будут в папке `exports/`

Подробная инструкция: [docs/deployment.md](docs/deployment.md)

