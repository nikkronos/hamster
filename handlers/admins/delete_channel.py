import logging

from aiogram import types
from aiogram.dispatcher.filters import Text

from keyboards.keyboards import get_keyboard
from loader import dp
from database.getters import get_data
from database.setters import delete_data
from database.work_db import execute_query
from validators import validate_channel_id, validate_channel_id_for_column_name


@dp.callback_query_handler(Text("select_delete_channel"))
async def select_delete_channel(call: types.CallbackQuery):
    """Выбор канала для удаления"""
    await call.answer()
    logging.info(f"Админ {call.from_user.id} начал удаление канала")
    # await call.message.answer("Идёт загрузка списка каналов...")
    tracked_channels = await get_data("tracked_channels", fetch="all")
    if not tracked_channels:
        await call.message.answer(
            "Нет каналов",
            reply_markup=await get_keyboard([[("Назад", "start")]]),
        )
    else:
        channels = []

        for channel in tracked_channels:
            channels.append(
                (channel["title"], f'delete_channel_{channel["channel_id"]}')
            )

        await call.message.answer(
            "Выберите канал для удаления",
            reply_markup=await get_keyboard([channels]),
        )


@dp.callback_query_handler(Text(startswith="delete_channel_"))
async def delete_channel(call: types.CallbackQuery):
    """Удаление канала из БД"""
    await call.answer()
    
    try:
        channel_id_raw = call.data.split("_")[-1]
        channel_id = validate_channel_id(channel_id_raw)
        # Валидация channel_id для использования в SQL
        channel_id_str = validate_channel_id_for_column_name(channel_id)
    except ValueError as e:
        logging.error(f"Ошибка валидации channel_id при удалении: {e}")
        await call.message.answer(
            "Ошибка: невалидный ID канала",
            reply_markup=await get_keyboard([[("Назад", "start")]]),
        )
        return
    
    try:
        await delete_data("tracked_channels", channel_id=channel_id)
    except Exception as e:
        logging.error(f"Ошибка при удалении канала из tracked_channels: {e}")
        await call.message.answer(
            "Ошибка при удалении канала из базы данных",
            reply_markup=await get_keyboard([[("Назад", "start")]]),
        )
        return

    try:
        # Валидация channel_id_str гарантирует, что это безопасное значение
        query = f"""
                ALTER TABLE user_links
                DROP COLUMN "{channel_id_str}";
                """
        await execute_query(query)
    except Exception as e:
        logging.error(f"Ошибка при удалении столбца из user_links: {e}")
        # Столбец может не существовать, это не критично
        pass

    logging.info(f"Канал {channel_id} успешно удален админом {call.from_user.id}")
    await call.message.answer(
        "Канал успешно удален",
        reply_markup=await get_keyboard([[("Назад", "start")]]),
    )
