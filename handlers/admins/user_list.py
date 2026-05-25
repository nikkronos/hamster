from aiogram import types
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from keyboards.keyboards import get_keyboard
from loader import dp


@dp.callback_query_handler(Text(startswith="user_list_"))
async def user_list(call: types.CallbackQuery):
    """Список пользователей"""
    await call.answer()

    subscribers = await get_data("user_subscriptions", fetch="all")
    if not subscribers:
        await call.message.answer("У вас нет подписчиков")
        return
    
    subs_list = []
    offset = int(call.data.split("_")[-1])
    limit = 30
    buttons = [[("Начальный экран", "start")]]
    buttons_nav = []

    header = f"{'First Name'.ljust(15)} | {'Username'.ljust(20)} | Subscription End"
    subs_list.append(header)
    subs_list.append("-" * len(header))

    for subscriber in subscribers[offset : offset + limit]:
        first_name, username = await get_data(
            table_name="users",
            select="first_name, username",
            fetch="one",
            user_id=subscriber["user_id"],
        )
        username_display = "@" + username if username else ""
        end_date = subscriber["datetime_end_subscribe"][:-7]

        subs_list.append(
            f"{first_name[:15].ljust(15)} | {username_display.ljust(20)} | {end_date}"
        )

        result = "\n".join(subs_list)

    if offset != 0:
        buttons_nav.append(("⏮", f"user_list_{offset - limit}"))

    if len(subscribers[offset + limit :]) != 0:
        buttons_nav.append(("⏭", f"user_list_{offset + limit}"))

    buttons.append(buttons_nav)

    await call.message.answer(
        text="<pre>" + result + "</pre>",
        parse_mode="HTML",
        reply_markup=await get_keyboard(buttons, row_width=2),
    )
