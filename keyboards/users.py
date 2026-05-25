from data import config
from keyboards.keyboards import get_keyboard
from database.getters import get_data


async def start(user_id):
    """Стартовое меню"""
    buttons = [
        [
            ("Купить", "about_subscribe"),
            ("Проверить свою подписку", "check_subscribe"),
        ]
    ]

    if await get_data("user_subscriptions", user_id=user_id):
        buttons[0].append(("Список каналов", "channel_list"))

    if user_id in config.ADMINS:
        buttons[0].append(("Меню админа", "menu_admin"))

    if user_id in config.DEVELOPERS:
        buttons[0].append(("Меню разработчика", "menu_developer"))

    return await get_keyboard(buttons)


async def cancel_button(b_name="❌"):
    """Кнопка отмены"""
    buttons = [[(b_name, "cancel")]]

    return await get_keyboard(buttons)
