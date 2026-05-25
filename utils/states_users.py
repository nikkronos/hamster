from aiogram.dispatcher import FSMContext

from loader import dp


async def get_state_user(user_id: int) -> FSMContext:
    """Возвращает state"""
    state = dp.current_state(chat=user_id, user=user_id)
    return state


async def reset_state_user(user_id: int, clear_data=False):
    """Сбрасывает state"""
    state = await get_state_user(user_id)
    await state.reset_state(with_data=clear_data)


async def save_data_state(user_id, **kwargs):
    """Сохранение данных в state"""
    state = await get_state_user(user_id)
    await state.update_data(**kwargs)


async def get_data_from_state(user_id, key, default_value=None):
    """Возвращает данные из state"""
    state = await get_state_user(user_id)
    return (await state.get_data()).get(key, default_value)


async def set_state(user_id: int, state: str):
    """Устанавливает состояние"""
    current_state = await get_state_user(user_id)
    await current_state.set_state(state)
