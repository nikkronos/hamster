keys = {
    # Пользователи
    "users": {
        "user_id": "INTEGER PRIMARY KEY",
        "first_name": "TEXT",
        "username": "TEXT",
        "date_reg": "TIMESTAMP",
    },
    # Каналы
    "channels": {
        "id": "INTEGER PRIMARY KEY",
        "channel_id": "INTEGER",
        "title": "TEXT",
    },
    # Отслеживаемые каналы
    "tracked_channels": {
        "id": "INTEGER PRIMARY KEY",
        "channel_id": "INTEGER",
        "title": "TEXT",
        "forward_channel_id": "INTEGER",
    },
    # Промокоды
    "promocodes": {
        "id": "INTEGER PRIMARY KEY",
        "promocode": "TEXT",
        "percent": "INTEGER",
        "expiration": "TIMESTAMP",
    },
    # Данные медиа
    "media_data": {
        "id": "INTEGER PRIMARY KEY",
        "type_media": "TEXT",
        "file_id": "TEXT",
        "media_group_id": "INTEGER",
        "caption": "TEXT",
        "caption_entities": "TEXT",
    },
    # Оплаты
    "payments": {
        "id": "INTEGER PRIMARY KEY",
        "user_id": "INTEGER",
        "amount": "TEXT",
        "promocode": "TEXT",
        "is_paid": "INTEGER",
        "date": "TIMESTAMP",
    },
    # Задачи для планировщика
    "tasks_for_scheduler": {
        "id": "INTEGER PRIMARY KEY",
        "user_id": "INTEGER",
        "run_date": "TIMESTAMP",
        "name": "TEXT",
    },
    # Подписки пользователей
    "user_subscriptions": {
        "id": "INTEGER PRIMARY KEY",
        "user_id": "INTEGER",
        "datetime_end_subscribe": "TIMESTAMP",
    },
    # Ссылки на каналы
    "user_links": {
        "user_id": "INTEGER PRIMARY KEY",
        #"channel_id": "TEXT", # link
    },
}


async def get_keys_for_query(keys):
    """Возвращает ключи для запроса"""
    variables = str(keys)
    values = ", ".join(["?" for _ in keys])

    return variables, values


async def get_keys_table(table_name):
    """Возвращает ключи таблицы"""
    return list(keys[table_name].keys())
