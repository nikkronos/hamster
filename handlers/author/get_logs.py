import asyncio

from aiogram import types

from data import config
from loader import dp


@dp.message_handler(commands='get_logs')
async def get_logs(message: types.Message):
    """Возвращает логи"""
    if message.from_user.id != config.DEVELOPER_ID:
        return

    paths_files = [
        '/home/hamster93_bot/loggs/logs.txt',
        '/home/hamster93_userbot/loggs/logs.txt',
    ]
    for path in paths_files:
        file = open(path, 'rb')
        await dp.bot.send_document(
            message.from_user.id,
            document=file
        )
        file.close()
        await asyncio.sleep(0.5)