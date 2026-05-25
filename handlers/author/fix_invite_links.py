from aiogram import types
from aiogram.dispatcher.filters import Text

import logging
from loader import dp
from database.getters import get_data
from database.setters import update_data


@dp.callback_query_handler(Text("fix_links"))
async def fix_links(call: types.CallbackQuery):
    await call.answer()

    tracked_channels_ids = await get_data(
        "tracked_channels", "forward_channel_id", fetch="all"
    )

    user_links = await get_data("user_links", fetch="all")

    for user in user_links:
        for id, link in enumerate(user):
            if link == "empty":
                try:
                    chat_id = tracked_channels_ids[id]  # name of the column
                    user_id = user[0]
                    invite_data = await dp.bot.create_chat_invite_link(
                        chat_id=chat_id,
                        member_limit=1,
                    )
                    await update_data(
                        "user_links",
                        set={f'"{chat_id}"': invite_data.invite_link},
                        where={"user_id": user_id},
                    )
                except Exception as ex:
                    logging.error(
                        f"Не удалось создать пригласительную ссылку в {chat_id}\n"
                        f"Причина: {ex}"
                    )

    await dp.bot.send_message(chat_id=call.from_user.id, text="Готово")
