import datetime
from aiogram import types
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from database.setters import delete_data
from keyboards.keyboards import get_keyboard
from loader import dp, scheduler
from utils.misc import add_scheduler_task


@dp.callback_query_handler(Text("add_reminder_3_days"))
async def fix_reminder(call: types.CallbackQuery):
    """Добавить напоминальку за 3 дня до окончания подписки"""
    await call.answer()

    subscribers_id = await get_data("user_subscriptions", "user_id", fetch="all")

    for user_id in subscribers_id:
        user_subscribe = await get_data("user_subscriptions", user_id=user_id)
        datetime_end_subscribe = datetime.datetime.strptime(
            user_subscribe["datetime_end_subscribe"], "%Y-%m-%d %H:%M:%S.%f"
        )
        # Добавление удаления по расписанию
        await add_scheduler_task(
            "end_subscribe",
            user_id,
            datetime_end_subscribe,
        )
        # Добавление напоминания об окончании подписки 1 день
        await add_scheduler_task(
            "reminder_1day",
            user_id,
            datetime_end_subscribe - datetime.timedelta(days=1),
        )
        # Добавление напоминания об окончании подписки 3 дня
        await add_scheduler_task(
            "reminder_3days",
            user_id,
            datetime_end_subscribe - datetime.timedelta(days=3),
        )

    await call.message.answer(f"Всем добавлена напоминалка")
