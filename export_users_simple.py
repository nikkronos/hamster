"""
Простой скрипт для экспорта пользователей в CSV
Скопируйте этот файл на сервер и запустите: python export_users_simple.py
"""
import asyncio
import csv
import os
import datetime
import sqlite3

DB_PATH = 'database/database.sqlite'


def get_connect():
    """Подключение к БД"""
    return sqlite3.connect(DB_PATH)


async def get_all_users():
    """Получить всех пользователей"""
    conn = get_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, first_name, username, date_reg FROM users")
    users = cursor.fetchall()
    conn.close()
    
    result = []
    for user in users:
        result.append({
            'user_id': user[0],
            'first_name': user[1] or '',
            'username': user[2] or '',
            'date_reg': user[3] or ''
        })
    return result


async def get_active_subscriptions():
    """Получить активные подписки"""
    conn = get_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, datetime_end_subscribe FROM user_subscriptions")
    subscriptions = cursor.fetchall()
    conn.close()
    
    result = {}
    for sub in subscriptions:
        result[sub[0]] = sub[1]
    return result


async def export_users(include_past=True):
    """Экспорт пользователей в CSV"""
    # Создаем папку для экспорта
    os.makedirs('exports', exist_ok=True)
    
    # Получаем данные
    all_users = await get_all_users()
    active_subs = await get_active_subscriptions()
    
    # Фильтруем пользователей
    if include_past:
        users_to_export = all_users
        filename = f"exports/all_users_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    else:
        users_to_export = [u for u in all_users if u['user_id'] in active_subs]
        filename = f"exports/active_users_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    if not users_to_export:
        print("Нет пользователей для экспорта")
        return None
    
    # Создаем CSV
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['user_id', 'username', 'first_name', 'subscription_status', 'subscription_end_date', 'date_reg'])
        
        for user in users_to_export:
            user_id = user['user_id']
            subscription_status = 'active' if user_id in active_subs else 'inactive'
            subscription_end_date = active_subs.get(user_id, '')
            
            writer.writerow([
                user_id,
                user['username'],
                user['first_name'],
                subscription_status,
                subscription_end_date,
                user['date_reg']
            ])
    
    return filename


async def main():
    print("Начинаю экспорт пользователей...")
    
    try:
        # Экспорт всех
        file1 = await export_users(include_past=True)
        if file1:
            print(f"✅ Все пользователи: {file1}")
        
        # Экспорт активных
        file2 = await export_users(include_past=False)
        if file2:
            print(f"✅ Активные пользователи: {file2}")
        
        print("✅ Экспорт завершен!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())


























