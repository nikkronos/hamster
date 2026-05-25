from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler

# ID пользователя, которого нужно проверять
BANNED_USERS = [1005818095]

class BannedUsersCheckMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        """
        Эта функция будет вызываться перед обработкой каждого сообщения.
        """
        # Проверяем, что ID пользователя совпадает с нужным
        if message.from_user.id in BANNED_USERS:
            # Отправляем специальное сообщение
            await message.answer("Это особое сообщение для наказанных! 🕵️‍♂️")
            
            # Если вы хотите остановить дальнейшую обработку сообщения,
            # можно раскомментировать следующую строку:
            raise CancelHandler()
        
    async def on_pre_process_callback_query(self, callback: types.CallbackQuery, data: dict):
        """
        Этот метод перехватывает ВСЕ НАЖАТИЯ НА ИНЛАЙН-КНОПКИ.
        """
        if callback.from_user.id == BANNED_USERS:
            # Отвечаем на сам колбэк, чтобы убрать "часики" на кнопке
            await callback.answer("Доступ заблокирован.", show_alert=True)
            # Останавливаем дальнейшую обработку
            raise CancelHandler()
        
        
# Отмена по разработке, денег не будет