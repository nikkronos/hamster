# База данных

## Общая информация

Используется **SQLite**. Файл базы данных: `database/database.sqlite`

## Структура таблиц

### 1. `users` - Пользователи

Хранит информацию о всех пользователях бота.

| Поле | Тип | Описание |
|------|-----|----------|
| `user_id` | INTEGER PRIMARY KEY | Telegram ID пользователя |
| `first_name` | TEXT | Имя пользователя |
| `username` | TEXT | Username (может быть NULL) |
| `date_reg` | TIMESTAMP | Дата регистрации |

### 2. `tracked_channels` - Отслеживаемые каналы

Хранит информацию о каналах, которые отслеживаются и копируются.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER PRIMARY KEY | ID записи |
| `channel_id` | INTEGER | ID канала-источника (откуда копировать) |
| `title` | TEXT | Название канала |
| `forward_channel_id` | INTEGER | ID канала-назначения (куда копировать, куда давать доступ) |

**Примечание:** `channel_id` используется как имя столбца в таблице `user_links` для хранения пригласительных ссылок.

### 3. `user_subscriptions` - Подписки пользователей

Хранит информацию о подписках пользователей.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER PRIMARY KEY | ID записи |
| `user_id` | INTEGER | Telegram ID пользователя |
| `datetime_end_subscribe` | TIMESTAMP | Дата и время окончания подписки |

**Логика:** Если `datetime_end_subscribe` в будущем - подписка активна. Если в прошлом или нет записи - подписки нет.

### 4. `user_links` - Пригласительные ссылки

Хранит пригласительные ссылки для доступа к каналам.

| Поле | Тип | Описание |
|------|-----|----------|
| `user_id` | INTEGER PRIMARY KEY | Telegram ID пользователя |
| `"{channel_id}"` | TEXT | Пригласительная ссылка для канала (динамический столбец) |

**Примечание:** Структура таблицы динамическая - для каждого канала создается отдельный столбец с именем `"{channel_id}"`. Это не лучшая практика, но используется в текущей реализации.

### 5. `payments` - Платежи

Хранит историю платежей.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER PRIMARY KEY | ID записи |
| `user_id` | INTEGER | Telegram ID пользователя |
| `amount` | TEXT | Сумма платежа |
| `promocode` | TEXT | Использованный промокод (может быть NULL) |
| `is_paid` | INTEGER | Статус оплаты (0 - не подтверждена, 1 - подтверждена) |
| `date` | TIMESTAMP | Дата платежа |

### 6. `promocodes` - Промокоды

Хранит информацию о промокодах.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER PRIMARY KEY | ID записи |
| `promocode` | TEXT | Текст промокода |
| `percent` | INTEGER | Процент скидки |
| `expiration` | TIMESTAMP | Дата истечения промокода |

### 7. `tasks_for_scheduler` - Задачи для планировщика

Хранит задачи для APScheduler, которые восстанавливаются при перезапуске бота.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER PRIMARY KEY | ID записи |
| `user_id` | INTEGER | Telegram ID пользователя |
| `run_date` | TIMESTAMP | Дата и время выполнения задачи |
| `name` | TEXT | Тип задачи: `end_subscribe`, `reminder_1day`, `reminder_3days` |

## Работа с БД

### Функции получения данных

Используются функции из `database/getters.py`:

```python
# Получить одну запись
user = await get_data("users", user_id=123456)

# Получить все записи
all_users = await get_data("users", fetch="all")

# Получить конкретные поля
username = await get_data("users", select="username", user_id=123456)
```

### Функции изменения данных

Используются функции из `database/setters.py`:

```python
# Добавить новую запись
await add_new_data("users", data=(user_id, first_name, username, date_reg))

# Обновить запись
await update_data("users", set={"first_name": "New Name"}, where={"user_id": user_id})

# Удалить запись
await delete_data("users", user_id=user_id)
```

### Прямые SQL-запросы

Для сложных запросов используется `database/work_db.py`:

```python
from database.work_db import execute_query

query = "SELECT * FROM users WHERE date_reg > ?"
params = [datetime.datetime.now() - datetime.timedelta(days=30)]
result = await execute_query(query, params, fetch="all")
```

## Важные замечания

1. **Динамические столбцы в `user_links`**: Это не лучшая практика. В будущем стоит рефакторить на отдельную таблицу `user_channel_links` с полями `user_id`, `channel_id`, `invite_link`.

2. **Параметризованные запросы**: Всегда использовать параметризованные запросы (`?`) для предотвращения SQL-инъекций.

3. **Транзакции**: Для критических операций (создание подписки + генерация ссылок) использовать транзакции.

4. **Индексы**: В текущей реализации индексы не используются. Для оптимизации можно добавить индексы на часто используемые поля (`user_id`, `channel_id`).

## Миграции

В текущей реализации миграции не используются. При изменении структуры таблиц нужно:
1. Создать бэкап БД
2. Выполнить ALTER TABLE вручную
3. Обновить `database/keys.py` если изменилась структура


























