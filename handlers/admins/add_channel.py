import logging

from aiogram import types
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from database.setters import add_new_data, update_data
from loader import dp
from utils import states_users as su
from utils.misc import generate_invite_links
from database.work_db import execute_query
from validators import validate_channel_id, validate_channel_id_for_column_name


@dp.callback_query_handler(Text("select_channel"))
async def req_channel_id(call: types.CallbackQuery):
    """Запрашивает ID канала"""
    await call.answer()
    logging.info(f"Админ {call.from_user.id} начал добавление канала")
    await call.message.answer(
        "Отправьте ID канала, <b>откуда</b> нужно пересылать "
        "посты из выбранного канала\n"
        "\n"
        "ID можно узнать, в этом боте @username_to_id_bot\n"
        "\n"
        "Юзербот должен быть участником канала"
    )
    await su.set_state(call.from_user.id, "channel_id")


@dp.message_handler(state="channel_id")
async def temp(message: types.Message):
    """Выбор канала"""
    try:
        channel_id = validate_channel_id(message.text.strip())
    except ValueError as e:
        await message.answer(f"Ошибка: {e}\n\nПопробуйте снова:")
        return

    await su.save_data_state(message.from_user.id, channel_id=channel_id)
    await message.answer(
        "Отправьте ID канала, <b>куда</b> нужно пересылать "
        "посты из выбранного канала\n"
        "\n"
        "ID можно узнать, в этом боте @username_to_id_bot\n"
        "\n"
        "Юзербот должен быть администратором канала, "
        "а этот бот должен быть участником канала"
    )
    await su.set_state(message.from_user.id, "forward_channel_id")


@dp.message_handler(state="forward_channel_id")
async def save_channel(message: types.Message):
    """Сохранение канала"""
    try:
        forward_channel_id = validate_channel_id(message.text.strip())
        forward_chat_data = await dp.bot.get_chat(forward_channel_id)
    except ValueError as e:
        await message.answer(f"Ошибка валидации: {e}\n\nПопробуйте снова:")
        return
    except Exception as ex:
        logging.error(f"{ex}")
        await message.answer(
            "Не удалось добавить канал, попробуйте ещё раз\n\n"
            f"Ошибка: <code>{ex}</code>"
        )
        return

    try:
        channel_id = await su.get_data_from_state(message.from_user.id, "channel_id")
        # Валидация channel_id для использования в SQL
        channel_id_str = validate_channel_id_for_column_name(channel_id)
    except ValueError as e:
        logging.error(f"Ошибка валидации channel_id: {e}")
        await message.answer("Ошибка: невалидный ID канала")
        await su.reset_state_user(message.from_user.id, clear_data=True)
        return

    await su.reset_state_user(message.from_user.id, clear_data=True)

    try:
        await add_new_data(
            "tracked_channels",
            data=(
                channel_id,
                forward_chat_data.title,
                forward_chat_data.id,
            ),
        )

        # Создание нового столбца в бд ссылок
        # Валидация channel_id_str гарантирует, что это безопасное значение
        # SQLite требует кавычки для имен столбцов с цифрами
        query = f"""
                ALTER TABLE user_links
                ADD "{channel_id_str}" TEXT NULL;
                """
        await execute_query(query)
    except Exception as ex:
        logging.error(f"Ошибка при добавлении канала: {ex}")
        await message.answer(
            "Ошибка при добавлении канала в базу данных. Попробуйте снова."
        )
        return

    # Заполнение бд ссылок
    subscribers_ids = await get_data("user_subscriptions", "user_id", fetch="all")
    for user_id in subscribers_ids:
        try:
            links = await generate_invite_links(forward_channel_id)
            await update_data(
                "user_links",
                set={
                    f'"{channel_id_str}"': links[0]   # The first because it returns as a list
                },  # Используем валидированное значение
                where={"user_id": user_id},
            )
        except Exception as ex:
            logging.error(f"Ошибка при создании ссылки для пользователя {user_id}: {ex}")
            continue

    logging.info(f"Канал {channel_id} (forward: {forward_channel_id}) успешно добавлен админом {message.from_user.id}")
    await message.answer("Канал добавлен! ✅")
