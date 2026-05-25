import datetime

from aiogram import executor, Dispatcher, types

import utils, handlers  # НЕ ТРОГАТЬ БЕЗ ЭТОГО НЕ РАБОТАЕТ!!!
from database import work_db
from database.getters import get_data
from database.setters import delete_data
from loader import dp, scheduler
from utils.misc import ban_user, reminder_user
# from middlewares.filter_banned_users import BannedUsersCheckMiddleware


async def on_startup(dp: Dispatcher):
    """Действия при запуске бота"""
    print("Бот запущен!")

    # Создание БД и таблиц в ней
    await work_db.create_tables()

    await dp.bot.set_my_commands([types.BotCommand("start", "Перезапуск бота")])

    tasks_for_scheduler = await get_data("tasks_for_scheduler", fetch="all")
    if tasks_for_scheduler:
        for task_data in tasks_for_scheduler:
            run_date = datetime.datetime.strptime(
                task_data["run_date"], "%Y-%m-%d %H:%M:%S.%f"
            )
            if run_date < datetime.datetime.now():
                if task_data["name"] == "end_subscribe":
                    await ban_user(task_data["user_id"])
                if task_data["name"] == "reminder":
                    await reminder_user(task_data["user_id"])
                await delete_data("tasks_for_scheduler", id=task_data["id"])
                continue

            if task_data["name"] == "end_subscribe":    # Если будет много вариантов, то надо модульное решение сделать
                scheduler.add_job(
                    func=ban_user,
                    trigger="date",
                    run_date=run_date,
                    args=[task_data["user_id"]],
                    id=f'end_subscribe_{task_data["user_id"]}',
                )
            elif task_data["name"] == "reminder_1day":
                scheduler.add_job(
                    func=reminder_user,
                    trigger="date",
                    run_date=run_date,
                    args=[task_data["user_id"]],
                    id=f'reminder_1day_{task_data["user_id"]}',
                )
            elif task_data["name"] == "reminder_3days":
                scheduler.add_job(
                    func=reminder_user,
                    trigger="date",
                    run_date=run_date,
                    args=[task_data["user_id"]],
                    id=f'reminder_3days_{task_data["user_id"]}',
                )


if __name__ == "__main__":
    scheduler.start()
    # dp.middleware.setup(BannedUsersCheckMiddleware())
    executor.start_polling(
        dp, on_startup=on_startup, allowed_updates=types.AllowedUpdates.all()
    )
