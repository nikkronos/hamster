import datetime

from aiogram import types
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from keyboards.keyboards import get_keyboard
from loader import dp


@dp.callback_query_handler(Text("check_subscribe"))
async def check_subscribe(call: types.CallbackQuery):
    """Проверка подписки"""
    user_subscribe = await get_data("user_subscriptions", user_id=call.from_user.id)
    if not user_subscribe:
        await call.message.answer(
            "У вас нет подписки 😥",
            reply_markup=await get_keyboard(
                [
                    [
                        ("Купить", "about_subscribe"),
                        ("Назад", "start"),
                    ]
                ]
            ),
        )

    else:
        datetime_end_subscribe = datetime.datetime.strptime(
            user_subscribe["datetime_end_subscribe"], "%Y-%m-%d %H:%M:%S.%f"
        ).strftime("%d.%m.%Y %H:%M")
        await call.message.answer(
            f"⏳ Подписка <b>активна</b> и действует до <b>{datetime_end_subscribe}</b>",
            reply_markup=await get_keyboard(
                [
                    [
                        ("Продлить", "about_subscribe"),
                        ("Назад", "start"),
                    ]
                ]
            ),
        )
    await call.answer()
