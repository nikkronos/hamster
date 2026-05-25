import asyncio
import logging
import datetime

from aiogram import types
from aiogram.dispatcher.filters import Text

from data import config
from database.getters import get_data
from database.setters import add_new_data
from keyboards.keyboards import get_keyboard
from loader import dp
from utils import states_users as su, misc


@dp.callback_query_handler(Text(startswith="req_scrn_pay_"))
async def req_screenshot(call: types.CallbackQuery):
    """Запрашивает скриншот оплаты"""
    if await su.get_data_from_state(call.from_user.id, "activate_promocode"):
        price = await su.get_data_from_state(call.from_user.id, "amount")
    else:
        months = int(call.data.split("_")[-1])

        match months:
            case 1:
                price = config.PRICE_1_MONTH
            case 3:
                price = config.PRICE_3_MONTHS
            case 6:
                price = config.PRICE_6_MONTHS
            case 12:
                price = config.PRICE_12_MONTHS
            case _:
                price = config.PRICE_1_MONTH

        await su.save_data_state(call.from_user.id, amount=price)
        await su.save_data_state(call.from_user.id, months=months)
    await call.message.answer(
        f"Отправьте {await misc.get_number_with_spaces(price)} "
        f"рублей на номер карты {config.BANK_CARD} (Т-Банк)\n"
        f"\n"
        f"После оплаты отправьте скриншот "
        f"(Чек отправлять не нужно, только скриншот)",
        reply_markup=await get_keyboard([[("Назад", "start")]]),
    )
    await su.set_state(call.from_user.id, "scrn_pay")
    await call.answer()


@dp.message_handler(state="scrn_pay", content_types=["photo", "document"])
async def send_screenshot_admin(message: types.Message):
    """Отправка скриншота админам"""
    await su.reset_state_user(message.from_user.id)
    await message.answer("Ожидайте проверки оплаты администратором")
    promocode = await su.get_data_from_state(message.from_user.id, "activate_promocode")
    months = await su.get_data_from_state(message.from_user.id, "months")
    amount = await su.get_data_from_state(message.from_user.id, "amount")
    paid_id = await add_new_data(
        "payments",
        data=(
            message.from_user.id,
            amount,
            promocode,
            0,
            datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        ),
    )

    params_msg = {
        "reply_markup": await get_keyboard(
            [
                [
                    (f"Подтвердить на {months*30} дней", f"confirm_pay_{months}_{paid_id}"),
                    ("Подтвердить на другое число дней", f"confirm_custom_pay_{paid_id}"),
                ]
            ]
        ),
        "caption": (
            f"Проверьте оплату от "
            f"{await misc.get_user_profile(message.from_user.id)}\n\n"
            f"Подписка куплена за {amount} рублей на {months} месяц"
        ),
    }
    
    if months > 1: params_msg["caption"] += "ев" 

    if promocode:
        promocode_data = await get_data("promocodes", promocode=promocode)
        params_msg["caption"] += (
            "\n\n"
            f"<b>Активированный промокод:</b> {promocode}\n"
            f'<b>Скидка:</b> {promocode_data["percent"]}%\n'
        )

    if "photo" in message:
        func_send_msg = dp.bot.send_photo
        params_msg["photo"] = message.photo[-1].file_id
    else:
        func_send_msg = dp.bot.send_document
        params_msg["document"] = message.document.file_id

    for chat_id in config.ADMINS:
        params_msg["chat_id"] = chat_id
        try:
            await func_send_msg(**params_msg)
        except Exception as ex:
            logging.error(
                f"Не удалось отправить скриншот оплаты админу {chat_id}\n" f"{ex}"
            )
            await message.answer("Не удалось отправить скриншот оплаты админу")

        await asyncio.sleep(0.05)
