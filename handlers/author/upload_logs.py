import os

from aiogram import types
from aiogram.dispatcher.filters import Text

from loader import dp


@dp.callback_query_handler(Text("upload_logs"))
async def upload_logs(call: types.CallbackQuery):
    """Upload logs"""
    await call.answer()
    dir_name = "loggs"
    file_list = os.listdir(dir_name)[:5]
    file_open_list = []
    media = []

    for file in file_list:
        file_open = open(f"{dir_name}/{file}", "rb")
        file_open_list.append(file_open)
        media.append(types.InputMediaDocument(file_open))

    await call.message.answer_media_group(media)

    for file_open in file_open_list:
        file_open.close()


@dp.callback_query_handler(Text("upload_logs_userbot"))
async def upload_logs(call: types.CallbackQuery):
    """Upload loggs for userbot"""
    await call.answer()
    path = "../hamster93_userbot/loggs"
    file_list = os.listdir(path)[:5]
    file_open_list = []
    media = []

    for file in file_list:
        file_open = open(f"{path}/{file}", "rb")
        file_open_list.append(file_open)
        media.append(types.InputMediaDocument(file_open))

    await call.message.answer_media_group(media)

    for file_open in file_open_list:
        file_open.close()


@dp.callback_query_handler(Text("upload_logs_userbot_last"))
async def upload_logs(call: types.CallbackQuery):
    """Upload last log file for userbot"""
    await call.answer()
    path = "../hamster93_userbot/loggs"
    file = "logs.txt"
    
    file_open = open(f"{path}/{file}", "rb")
    media = [types.InputMediaDocument(file_open)]

    await call.message.answer_media_group(media)

    file_open.close()
