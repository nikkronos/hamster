from aiogram import types
from aiogram.dispatcher.filters import Text

import keyboards
from data import config
from loader import dp


@dp.message_handler(commands="developer")
@dp.callback_query_handler(Text("menu_developer"))
async def menu_developer(message: types.Message):
    """Меню разработчика"""
    if "data" in message:
        call: types.CallbackQuery = message
        await call.answer()

    user_id = message.from_user.id
    if user_id not in config.DEVELOPERS:
        return

    await dp.bot.send_message(
        chat_id=message.from_user.id,
        text=("Меню разработчика"),
        reply_markup=await keyboards.developer.menu_developer(),
    )
