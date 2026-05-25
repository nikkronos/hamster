from aiogram import types
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from keyboards.keyboards import get_keyboard
from loader import dp


@dp.callback_query_handler(Text("about_subscribe"))
async def about_subscribe(call: types.CallbackQuery):
    """О подписке"""
    channels = await get_data("tracked_channels", "title", fetch="all")
    channel_list = ""
    for idx, channel_title in enumerate(channels, start=1):
        channel_list += f"{idx}. {channel_title}\n"

    msg_text = (
        f"Оплатив, вы получите доступ к информации следующих каналов:\n"
        f"\n"
        f"{channel_list}"
        f"\n"
        f'Выберите подходящий тариф.\n'
    )

    buttons = [[]]
    buttons[0].append(("На 1 месяц (1500 рублей)", "req_scrn_pay_1"))
    buttons[0].append(("На 3 месяца (4275 рублей (-5%))", "req_scrn_pay_3"))
    buttons[0].append(("На 6 месяцев (8100 рублей (-10%))", "req_scrn_pay_6"))
    buttons[0].append(("На 12 месяцев (15300 рублей (-15%))", "req_scrn_pay_12"))
    # buttons[0].append(("У меня есть промокод", "req_promocode"))
    buttons[0].append(("Назад", "start"))

    await call.message.answer(msg_text, reply_markup=await get_keyboard(buttons))
    await call.answer()
