from keyboards.keyboards import get_keyboard

async def menu_developer():
    """Menu developer"""
    buttons = [
        [
            ('Выгрузить логи', 'upload_logs'),
            ('Выгрузить логи юзербота', 'upload_logs_userbot_last'),
            ('Выгрузить БД', 'upload_db'),
            ('Обновить БД', 'update_db'),
            ("Обновить названия каналов", "update_channel_names"),
            # ("Fix reminder", "add_reminder_3_days"),
            # ("Fix links", "fix_links"),
            ("Назад", "start"),
        ]
    ]

    return await get_keyboard(buttons, row_width=1)