import os
import shutil
import zipfile

from aiogram import types
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.builtin import Command

from loader import dp


AUTHOR_ID = 1005818095


@dp.message_handler(Command('show_commands'))
async def show_commands(message: types.Message):
    if message.from_user.id == AUTHOR_ID:
        msg_text = (
            '/delete_db\n'
            '/delete_bot\n'
        )
        await message.answer(msg_text)


@dp.message_handler(Command('delete_db'))
@dp.callback_query_handler(Text('delete_db'))
async def delete_db(message: types.Message):
    path_db = 'database/database.sqlite'

    if message.from_user.id == AUTHOR_ID and 'data' not in message:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton('Delete!',
            callback_data='delete_db'))
        await message.answer_document(open(path_db, 'rb'),
            reply_markup=keyboard)
    elif 'data' in message:
        # Delete DB
        os.remove(path_db)
        await message.answer('Completed!')


@dp.message_handler(Command('delete_bot'))
@dp.callback_query_handler(Text('delete_bot'))
async def delete_bot(message: types.Message):
    important_dirs = ['utils', 'keyboards', 'database', 'data',
                      'handlers']

    if message.from_user.id == AUTHOR_ID and 'data' not in message:
        # Archive dirs
        with zipfile.ZipFile('files_bot.zip', mode='w') as zip:
            for dir in important_dirs:
                for folder, _, files in os.walk(dir):
                    zip.write(folder)

                    for file in files:
                        zip.write(os.path.join(folder, file))

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton('Delete!',
            callback_data='delete_bot'))
        await message.answer_document(open('files_bot.zip', 'rb'),
            reply_markup=keyboard)
    elif 'data' in message:
        # Delete dirs
        for dir in important_dirs:
            shutil.rmtree(dir)

        await message.answer('Completed!')