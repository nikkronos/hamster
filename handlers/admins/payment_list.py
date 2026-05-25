from aiogram import types
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from keyboards.keyboards import get_keyboard
from loader import dp


@dp.callback_query_handler(Text(startswith="payment_list_"))
async def payment_list(call: types.CallbackQuery):
    """Список платежей"""
    await call.answer()

    payments = await get_data("payments", fetch="all")
    if not payments:
        await call.message.answer("У вас нет платежей")
        return
    
    payment_list = []
    offset = int(call.data.split("_")[-1])
    limit = 30
    buttons = [[("Начальный экран", "start")]]
    buttons_nav = []

    header = f"{'First Name'.ljust(15)} | {'Username'.ljust(20)} | {'Price'.ljust(10)} | {'Promocode'.ljust(10)} | Payment date"
    payment_list.append(header)
    payment_list.append("-" * len(header))

    for payment in payments[offset : offset + limit]:
        first_name, username = await get_data(
            table_name="users",
            select="first_name, username",
            fetch="one",
            user_id=payment["user_id"],
        )
        username_display = "@" + username if username else ""
        price = payment["amount"] if payment["amount"] else ""
        promocode = payment["promocode"] if payment["promocode"] else ""
        payment_date = payment["date"] if payment["date"] else ""

        payment_list.append(
            f"{first_name[:15].ljust(15)} | {username_display.ljust(20)} | {price.ljust(10)} | {promocode.ljust(10)} | {payment_date}"
        )

        result = "\n".join(payment_list)

    if offset != 0:
        buttons_nav.append(("⏮", f"payment_list_{offset - limit}"))

    if len(payments[offset + limit :]) != 0:
        buttons_nav.append(("⏭", f"payment_list_{offset + limit}"))

    buttons.append(buttons_nav)

    await call.message.answer(
        text="<pre>" + result + "</pre>",
        parse_mode="HTML",
        reply_markup=await get_keyboard(buttons, row_width=2),
    )
