from aiogram import types


async def get_inline_button(button_data):
    """Возвращает inline-кнопку"""
    text, data = button_data
    params_button = {"text": text}

    if data.startswith("http"):
        params_button["url"] = data
    else:
        params_button["callback_data"] = data

    return types.InlineKeyboardButton(**params_button)


async def get_keyboard(buttons_user, type_kb="inline", row_width=1):
    """Генерирует и возвращает клавиатуру"""
    if type_kb == "inline":
        keyboard = types.InlineKeyboardMarkup(row_width=row_width)
        buttons = []

        for i in buttons_user:
            if type(i) == list:
                row = []

                for b_data in i:
                    row.append(await get_inline_button(b_data))

                buttons.append(row)
            else:
                buttons.append(await get_inline_button(i))
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
        buttons = []

        for i in buttons_user:
            if type(i) == list:
                row = []

                for text in i:
                    row.append(types.KeyboardButton(text))

                buttons.append(row)
            else:
                buttons.append(types.KeyboardButton(i))

    for row in buttons:
        keyboard.add(*row)

    return keyboard
