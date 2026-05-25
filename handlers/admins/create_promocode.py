import datetime
import random
import string

from aiogram import types
from aiogram.dispatcher.filters import Text

from loader import dp
import keyboards
from keyboards.keyboards import get_keyboard
from utils import states_users as su
from database.setters import add_new_data


@dp.callback_query_handler(Text("create_promocode"))
async def req_percent(call: types.CallbackQuery):
    """Запрашивает процент"""
    await call.answer()
    await call.message.answer(
        "Отправьте процент скидки от 1 до 100, без лишних символов, только число",
        reply_markup=await keyboards.users.cancel_button(),
    )
    await su.set_state(call.from_user.id, "percent_promocode")


@dp.message_handler(
    lambda msg: 1 <= int(msg.text.strip()) <= 100, state="percent_promocode"
)
async def req_code(message: types.Message):
    """Запрашивает код"""
    await su.save_data_state(message.from_user.id, percent=int(message.text.strip()))
    await message.answer(
        "Отправьте промокод или нажмите кнопку, чтобы бот его создал за вас",
        reply_markup=await get_keyboard([[("Создать промокод", "create_random_code")]]),
    )
    await su.set_state(message.from_user.id, "code_for_promo")


@dp.callback_query_handler(Text("create_random_code"), state="code_for_promo")
@dp.message_handler(state="code_for_promo")
async def save_promocode(call: types.CallbackQuery):
    """Сохранение промокода"""
    if "data" in call:
        await call.message.delete()
        promocode = "".join(
            [random.choice(string.ascii_uppercase + string.digits) for _ in range(6)]
        )
    else:
        message: types.Message = call
        promocode = message.text.strip()

    percent = await su.get_data_from_state(call.from_user.id, "percent")
    await su.reset_state_user(call.from_user.id, clear_data=True)
    await add_new_data(
        "promocodes",
        data=(
            promocode,
            percent,
            datetime.datetime.now() + datetime.timedelta(days=30),
        ),
    )
    await dp.bot.send_message(
        chat_id=call.from_user.id,
        text=(
            "Промокод создан! ✅\n\n"
            f"<b>Промокод:</b> <code>{promocode}</code> (нажмите, "
            f"чтобы скопировать)\n"
            f"<b>Скидка:</b> {percent}%\n"
            f"<b>Действует до:</b> {str(datetime.datetime.now() + datetime.timedelta(days=30))[:20]}"
        ),
    )
