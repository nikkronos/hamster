from aiogram import types
from aiogram.dispatcher.filters import Text

import keyboards
from data import config
from loader import dp


@dp.message_handler(commands='admin')
@dp.callback_query_handler(Text('menu_admin'))
async def menu_admin(message: types.Message):
    """Меню админа"""
    if 'data' in message:
        call: types.CallbackQuery = message
        await call.answer()
        
    if message.from_user.id not in config.ADMINS:
        return

    await dp.bot.send_message(
        chat_id=message.from_user.id,
        text=(
            'Выберите действие:'
        ),
        reply_markup=await keyboards.admin.menu()
    )