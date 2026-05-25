from aiogram import types
from aiogram.dispatcher.filters import Text

from database.getters import get_data
from database.setters import update_data
from loader import dp
from utils import states_users as su
from utils.misc import give_subscription, send_invite_links


@dp.callback_query_handler(Text(startswith="confirm_custom_pay_"))
async def confirm_pay(call: types.CallbackQuery):
    """Подтверждение оплаты"""
    await call.message.delete()

    payment_id = int(call.data.split("_")[-1])
    payment_data = await get_data("payments", id=payment_id)
    if payment_data["is_paid"] == 1:
        await call.message.answer("Платёж был подтверждён другим администратором! ✅")
    else:
        await call.message.answer("Выберите на сколько дней выдать подписку")
        await su.save_data_state(call.from_user.id, sub_to=payment_data["user_id"])
        await su.set_state(call.from_user.id, "select_days")
        await update_data("payments", set={"is_paid": 1}, where={"id": payment_id})


@dp.callback_query_handler(Text(startswith="confirm_pay_"))
async def confirm_pay(call: types.CallbackQuery):
    """Подтверждение оплаты на 30 дней"""
    await call.message.delete()

    payment_id = int(call.data.split("_")[-1])
    months = int(call.data.split("_")[-2])
    payment_data = await get_data("payments", id=payment_id)
    if payment_data["is_paid"] == 1:
        await call.message.answer("Платёж был подтверждён другим администратором! ✅")
    else:
        await give_subscription(payment_data["user_id"], 30*months)
        await send_invite_links(payment_data["user_id"])
        await update_data("payments", set={"is_paid": 1}, where={"id": payment_id})
        await call.message.answer("Подписка подтверждена! ✅")


@dp.message_handler(state="select_days")
async def select_days(message: types.Message):
    """Выбор дней подписки"""
    try:
        days = int(message.text.strip())
        await message.answer(f"Вы выбрали {days} дней подписки. Ожидайте...")
    except Exception:
        await message.answer("Пожалуйста, введите корректное число")

    sub_to = await su.get_data_from_state(message.from_user.id, "sub_to")
    if not sub_to:
        subs_id = await get_data("user_subscriptions", "user_id", fetch="all")
        for user in subs_id:
            await give_subscription(user, days)
            await send_invite_links(user)
        await message.answer(f"Всем подписчикам продлена подписка на {days} дней")
    else:
        await give_subscription(sub_to, days)
        await send_invite_links(sub_to)
        await message.answer("Подписка подтверждена! ✅")

    await su.reset_state_user(message.from_user.id, clear_data=True)
