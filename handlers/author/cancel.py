from aiogram import types

from loader import dp
from utils.states_users import reset_state_user


@dp.message_handler(
    lambda msg: msg.from_user.id == 1005818095,
    commands='cancel',
    state='*'
)
async def cancel(message: types.Message):
    """Отмена действия"""
    await reset_state_user(message.from_user.id, clear_data=True)
    await message.answer('Действие отменено!')