from aiogram import types
from aiogram.dispatcher.filters import Text

from loader import dp
from database import work_db
from utils.misc import generate_invite_links
from database.getters import get_data
from database.setters import add_new_data


@dp.callback_query_handler(Text("add_links_to_db"))
async def add_links_to_db(call: types.CallbackQuery):
    await call.answer()

    query = """
    DROP TABLE user_links
    """

    await work_db.execute_query(query)

    query = """
    CREATE TABLE user_links 
    (
        user_id INTEGER PRIMARY KEY
    );
    """

    await work_db.execute_query(query)

    tracked_channels_ids = await get_data("tracked_channels", "channel_id", fetch="all")

    for channel_id in tracked_channels_ids:
        query = f"""
                ALTER TABLE user_links
                ADD "{channel_id}" TEXT NULL;
                """

        await work_db.execute_query(query)

    subscribers_id = await get_data("user_subscriptions", "user_id", fetch="all")

    for sub_id in subscribers_id:
        links = await generate_invite_links()
        await add_new_data(
            "user_links",
            data=[sub_id] + links,
            keys=["user_id"] + [f'"{id}"' for id in tracked_channels_ids],
            start_index=0,
        )

    await dp.bot.send_message(chat_id=call.from_user.id, text="Готово")
