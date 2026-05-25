"""
Валидация входных данных от пользователей
"""


def validate_user_id(user_id):
    """
    Валидация user_id
    
    Args:
        user_id: ID пользователя (может быть строкой или числом)
    
    Returns:
        int: Валидный user_id
    
    Raises:
        ValueError: Если user_id невалиден
    """
    try:
        user_id = int(user_id)
        if user_id <= 0:
            raise ValueError("user_id должен быть положительным числом")
        return user_id
    except (ValueError, TypeError):
        raise ValueError("user_id должен быть числом")


def validate_channel_id(channel_id):
    """
    Валидация channel_id
    
    Args:
        channel_id: ID канала (может быть строкой или числом)
    
    Returns:
        int: Валидный channel_id
    
    Raises:
        ValueError: Если channel_id невалиден
    """
    try:
        channel_id = int(channel_id)
        # Каналы в Telegram могут иметь отрицательные ID
        if channel_id == 0:
            raise ValueError("channel_id не может быть нулем")
        return channel_id
    except (ValueError, TypeError):
        raise ValueError("channel_id должен быть числом")


def validate_days(days):
    """
    Валидация количества дней подписки
    
    Args:
        days: Количество дней (может быть строкой или числом)
    
    Returns:
        int: Валидное количество дней
    
    Raises:
        ValueError: Если days невалидно
    """
    try:
        days = int(days)
        if days <= 0:
            raise ValueError("Количество дней должно быть положительным числом")
        if days > 3650:  # Максимум 10 лет
            raise ValueError("Количество дней не может превышать 3650")
        return days
    except (ValueError, TypeError):
        raise ValueError("Количество дней должно быть числом")


def validate_channel_id_for_column_name(channel_id):
    """
    Валидация channel_id для использования в имени столбца SQL
    
    Проверяет, что channel_id содержит только цифры (безопасно для SQL)
    
    Args:
        channel_id: ID канала
    
    Returns:
        str: Валидное имя столбца
    
    Raises:
        ValueError: Если channel_id невалиден для использования в SQL
    """
    channel_id = validate_channel_id(channel_id)
    
    # Проверяем, что channel_id содержит только цифры (для безопасности)
    # В SQLite имена столбцов в кавычках могут содержать любые символы,
    # но мы ограничиваемся только цифрами для безопасности
    channel_id_str = str(channel_id)
    if not channel_id_str.replace('-', '').isdigit():
        raise ValueError("channel_id содержит недопустимые символы для имени столбца")
    
    return channel_id_str


def validate_promocode(promocode):
    """
    Валидация промокода
    
    Args:
        promocode: Текст промокода
    
    Returns:
        str: Валидный промокод
    
    Raises:
        ValueError: Если промокод невалиден
    """
    if not promocode:
        raise ValueError("Промокод не может быть пустым")
    
    promocode = str(promocode).strip()
    
    if len(promocode) < 3:
        raise ValueError("Промокод должен содержать минимум 3 символа")
    
    if len(promocode) > 50:
        raise ValueError("Промокод не может содержать более 50 символов")
    
    # Разрешаем только буквы, цифры и некоторые символы
    if not all(c.isalnum() or c in ['-', '_'] for c in promocode):
        raise ValueError("Промокод может содержать только буквы, цифры, дефисы и подчеркивания")
    
    return promocode


def validate_percent(percent):
    """
    Валидация процента скидки
    
    Args:
        percent: Процент скидки (может быть строкой или числом)
    
    Returns:
        int: Валидный процент
    
    Raises:
        ValueError: Если percent невалиден
    """
    try:
        percent = int(percent)
        if percent < 1 or percent > 100:
            raise ValueError("Процент скидки должен быть от 1 до 100")
        return percent
    except (ValueError, TypeError):
        raise ValueError("Процент скидки должен быть числом от 1 до 100")


























