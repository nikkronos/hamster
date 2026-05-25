import asyncio
import logging

from aiogram import types
from aiogram import utils
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from database.setters import update_data
from loader import dp


@dp.callback_query_handler(Text("update_channel_names"))
async def update_channel_names(call: types.CallbackQuery):
    """Обновление имен каналов в бд"""
    await call.answer()
    forward_channels_ids = await get_data(
        "tracked_channels", "forward_channel_id", fetch="all"
    )
    for forward_channel_id in forward_channels_ids:
        while True:
            try:
                forward_chat_data = await dp.bot.get_chat(forward_channel_id)
                await update_data(
                    "tracked_channels",
                    set={"title": forward_chat_data.title},
                    where={"forward_channel_id": forward_channel_id},
                )  # Mb cause collision
                await dp.bot.send_message(
                    chat_id=call.from_user.id,
                    text=f"Обновлено название канала {forward_chat_data.title}",
                )
                break
            except utils.exceptions.RetryAfter as e:
                # Если поймали исключение RetryAfter, ждем указанное количество секунд
                await asyncio.sleep(e.timeout)
            except Exception as ex:
                logging.error(f"{ex}")
                await call.message.answer(
                    "Не удалось добавить канал, попробуйте ещё раз\n\n"
                    f"Ошибка: <code>{ex}</code>"
                )
                return

    await dp.bot.send_message(chat_id=call.from_user.id, text="Готово")
