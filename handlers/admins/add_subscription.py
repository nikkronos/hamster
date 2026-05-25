import datetime
from aiogram import types
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from keyboards.keyboards import get_keyboard
from loader import dp
from utils import states_users as su


@dp.callback_query_handler(Text(startswith="select_user_"))
async def select_user(call: types.CallbackQuery):
    """Выбрать пользователя из списка пользователей для продления подписки"""
    await call.answer()

    offset = int(call.data.split("_")[-1])
    users = await get_data("users", fetch="all")

    limit = 15
    part_users = users[offset : offset + limit]
    buttons = [[]]
    buttons_nav = []

    for user in part_users:
        name = user["first_name"]
        if user["username"]:
            username = "@" + user["username"]
        else:
            username = ""
        buttons[0].append((f"{name} {username}", f"add_subscription_{user['user_id']}"))

    if offset != 0:
        buttons_nav.append(("⏮", f"select_user_{offset - limit}"))

    if len(users[offset + limit :]) != 0:
        buttons_nav.append(("⏭", f"select_user_{offset + limit}"))

    buttons.append(buttons_nav)

    buttons[0].append(("Выбрать пользователя по id", "user_id_message"))

    await call.message.answer(
        "Выберите какому пользователю продлить подписку:",
        reply_markup=await get_keyboard(buttons),
    )


@dp.callback_query_handler(Text("user_id_message"))
async def user_id_message(call: types.CallbackQuery):
    """Сообщение про id пользователя"""
    await call.answer()
    await call.message.answer(
        "Отправьте ID пользователя \n"
        "\n"
        "ID можно узнать, в этом боте @username_to_id_bot\n"
    )
    await su.set_state(call.from_user.id, "user_id_input")


@dp.message_handler(state="user_id_input")
async def try_buy_subscription(message: types.Message):
    """Выбор пользователя по id"""
    user_id = message.text.strip()
    user_data = await get_data("users", user_id=user_id)
    if not user_data:
        await message.answer("Этот пользователь еще не пользовался этим ботом")
    else:
        await message.answer("Пользователь выбран успешно")
        await su.save_data_state(message.from_user.id, sub_to=user_id)
        await message.answer("Выберите на сколько дней выдать подписку")
        await su.set_state(message.from_user.id, "select_days")


@dp.callback_query_handler(Text(startswith="add_subscription_"))
async def add_subscription(call: types.CallbackQuery):
    """Добавление дней подписки"""
    await call.answer()
    user_id = call.data.split("_")[-1]
    if user_id.isdigit():
        await call.message.answer("Пользователь выбран успешно")
        await su.save_data_state(call.from_user.id, sub_to=user_id)
    await call.message.answer("Выберите на сколько дней выдать подписку")
    await su.set_state(call.from_user.id, "select_days")
