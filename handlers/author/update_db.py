from aiogram import types
from aiogram.dispatcher.filters import Text

from loader import dp
from utils.states_users import set_state, reset_state_user


@dp.callback_query_handler(Text('update_db'))
async def req_db(call: types.CallbackQuery):
    """Запрашивает БД"""
    await call.answer()
    await call.message.answer(
        'Отправьте новую БД'
    )
    await set_state(call.from_user.id, 'new_db_for_update')


@dp.message_handler(state='new_db_for_update', content_types=['document'])
async def update_db(message: types.Message):
    """Обновление БД"""
    await reset_state_user(message.from_user.id, clear_data=True)
    await dp.bot.download_file_by_id(
        message.document.file_id, destination='database/database.sqlite'
    )
    await message.answer('БД обновлена! ✅')