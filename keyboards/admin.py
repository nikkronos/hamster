from keyboards.keyboards import get_keyboard


async def menu():
    """Меню админа"""
    buttons = [
        [
            ("Добавить канал", "select_channel"),
            ("Удалить канал", "select_delete_channel"),
            ("Создать промокод", "create_promocode"),
            ("Посмотреть пользователей", "user_list_0"),
            ("Посмотреть платежи", "payment_list_0"),
            ("Рассылка", "broadcast"),
            ("Продлить подписку одному человеку", "select_user_0"),
            ("Продлить подписку всем", "add_subscription_to_everyone"),
            ("Назад", "start"),
        ]
    ]

    return await get_keyboard(buttons)
