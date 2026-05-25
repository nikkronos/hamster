from aiogram import types
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from keyboards.keyboards import get_keyboard
from loader import dp
from utils.misc import get_invite_links


@dp.callback_query_handler(Text("channel_list"))
async def channel_list(call: types.CallbackQuery):
    """Список каналов"""
    user_subscribe_id = await get_data("user_subscriptions", "user_id", user_id=call.from_user.id)
    if not user_subscribe_id:
        await call.message.answer("У вас нет подписки")

    else:
        await call.message.answer(
            text=(
                "Важный дисклеймер: здесь нет индивидуальных инвестиционных "
                "рекомендаций (ИИР), всю информацию необходимо использовать с "
                "личной ответственностью.\n"
                "\n"
                "Добавляйте каналы неспешно, канал в минуту. Так как у телеграма есть ограничение, "
                "то он может ограничить возможность добавлять новые каналы на какое-то время."
            ),
            reply_markup=await get_invite_links(user_subscribe_id),
        )

        await dp.bot.send_message(
            chat_id=call.from_user.id,
            text="Чтобы вернуться назад нажмите на кнопку <b>Начальный экран</b>",
            reply_markup=await get_keyboard([[("Начальный экран", "start")]]),
        )

    await call.answer()
