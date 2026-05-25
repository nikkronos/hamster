import datetime

from aiogram import types
from aiogram.dispatcher.filters import Text

from data import config
from database.getters import get_data
from keyboards.keyboards import get_keyboard
from loader import dp
from utils import states_users as su, misc


@dp.callback_query_handler(Text("req_promocode"))
async def req_promocode(call: types.CallbackQuery):
    """Запрашивает промокод"""
    await call.message.answer(
        "Отправьте промокод", reply_markup=await get_keyboard([[("Назад", "start")]])
    )
    await su.set_state(call.from_user.id, "promocode")
    await call.answer()


@dp.message_handler(state="promocode")
async def check_discount(message: types.Message):
    """Проверка скидки"""
    promocode_data = await get_data("promocodes", promocode=message.text.strip(), fetch="all")
    if not promocode_data:
        await message.answer(
            "Нет такого промокода! ❌ \n\nПроверьте и попробуйте ещё раз",
            reply_markup=await get_keyboard([[("Назад", "start")]]),
        )
        return

    promocode = promocode_data[-1]

    expiration_date = datetime.datetime.strptime(
        promocode["expiration"], "%Y-%m-%d %H:%M:%S.%f"
    )
    if expiration_date < datetime.datetime.now():
        await message.answer(
            "Этот промокод истек 😓",
            reply_markup=await get_keyboard([[("Назад", "start")]]),
        )
        return

    await su.reset_state_user(message.from_user.id)
    if promocode["percent"] < 100:
        new_price = round(config.PRICE_1_MONTH * (1 - promocode["percent"] / 100), 2)
        new_price = int(new_price) if new_price.is_integer() else new_price

        await su.save_data_state(message.from_user.id, amount=new_price)
        await su.save_data_state(
            message.from_user.id, activate_promocode=message.text.strip()
        )
        await message.answer(
            f"Промокод на {promocode['percent']}% скидки активирован! ✅",
            reply_markup=await get_keyboard(
                [
                    [
                        ("Оплатить с промокодом", "req_scrn_pay_1"),
                        ("Назад", "start"),
                    ]
                ]
            ),
        )
    else:
        await misc.give_subscription(message.from_user.id, 30)
        await misc.send_invite_links(message.from_user.id)
