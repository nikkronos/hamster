from aiogram import types
from aiogram.dispatcher.filters import Text

from loader import dp


@dp.callback_query_handler(Text('upload_db'))
async def upload_db(call: types.CallbackQuery):
    """Upload DB"""
    await call.answer()
    document = open('database/database.sqlite', 'rb')
    await call.message.answer_document(document)
    document.close()