"""
Скрипт для экспорта пользователей в CSV
Запуск: python scripts/export_users.py
"""
import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.admins.export_users import export_users_to_csv
from database.work_db import get_connect


async def main():
    """Основная функция"""
    print("Начинаю экспорт пользователей...")
    
    try:
        # Экспорт всех пользователей (включая неактивных)
        filepath = await export_users_to_csv(include_past_subscribers=True)
        print(f"✅ Экспорт завершен успешно!")
        print(f"📁 Файл сохранен: {filepath}")
        
        # Также экспортируем только активных
        filepath_active = await export_users_to_csv(include_past_subscribers=False)
        print(f"✅ Экспорт активных пользователей завершен!")
        print(f"📁 Файл сохранен: {filepath_active}")
        
    except Exception as e:
        print(f"❌ Ошибка при экспорте: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


























