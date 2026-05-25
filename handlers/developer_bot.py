from aiogram import types

from loader import dp


@dp.message_handler(commands="developer_bot")
async def developer_bot(message: types.Message):
    """Показывает разработчика бота"""
    await message.answer(
        "<b>💡 Идея:</b> @kronos_lolly\n"
        "<b>👨‍💻 Основатель:</b> @d_chistikov\n"
        "<b>🔧 Доработка:</b> @B3Max_xD"
    )
