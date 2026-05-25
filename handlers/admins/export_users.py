"""
Функция экспорта пользователей в CSV
Использование: создать скрипт для запуска этой функции или вызвать напрямую
"""
import csv
import os
import datetime
from database.getters import get_data


async def export_users_to_csv(include_past_subscribers=True, output_dir="exports"):
    """
    Экспорт пользователей в CSV файл
    
    Args:
        include_past_subscribers: Если True - экспортировать всех пользователей, 
                                  если False - только активных
        output_dir: Директория для сохранения файла
    
    Returns:
        str: Путь к созданному файлу
    """
    # Создаем директорию для экспорта, если её нет
    os.makedirs(output_dir, exist_ok=True)
    
    # Получаем всех пользователей
    all_users = await get_data("users", fetch="all")
    
    if not all_users:
        raise ValueError("В базе данных нет пользователей")
    
    # Получаем активные подписки
    active_subscriptions = await get_data("user_subscriptions", fetch="all")
    active_user_ids = {sub["user_id"] for sub in active_subscriptions} if active_subscriptions else set()
    
    # Фильтруем пользователей в зависимости от параметра
    if include_past_subscribers:
        # Все пользователи
        users_to_export = all_users
        filename = f"all_users_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    else:
        # Только пользователи с активной подпиской
        users_to_export = [user for user in all_users if user["user_id"] in active_user_ids]
        filename = f"active_users_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    if not users_to_export:
        raise ValueError("Нет пользователей для экспорта")
    
    # Путь к файлу
    filepath = os.path.join(output_dir, filename)
    
    # Создаем CSV файл
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        
        # Заголовки
        writer.writerow([
            "user_id",
            "username",
            "first_name",
            "subscription_status",
            "subscription_end_date",
            "date_reg"
        ])
        
        # Данные пользователей
        for user in users_to_export:
            user_id = user["user_id"]
            
            # Проверяем статус подписки
            subscription = await get_data("user_subscriptions", user_id=user_id)
            if subscription:
                subscription_status = "active"
                subscription_end_date = subscription["datetime_end_subscribe"]
            else:
                subscription_status = "inactive"
                subscription_end_date = ""
            
            writer.writerow([
                user_id,
                user.get("username", "") or "",
                user.get("first_name", "") or "",
                subscription_status,
                subscription_end_date,
                user.get("date_reg", "") or ""
            ])
    
    return filepath

