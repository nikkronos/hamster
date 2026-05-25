import asyncio
import datetime
import logging

from aiogram import utils

from database.getters import get_data
from database.setters import add_new_data, update_data, delete_data
from keyboards.keyboards import get_keyboard
from loader import dp, scheduler

from data.config import ADMINS

logger = logging.getLogger(__name__)


async def reminder_user(user_id):
    """Напоминалка для пользователя об окончании подписки"""
    logger.info(f"Отправка напоминания пользователю {user_id} об окончании подписки")
    
    try:
        if await get_data("tasks_for_scheduler", name="reminder_3days", user_id=user_id):
            await delete_data("tasks_for_scheduler", name="reminder_3days", user_id=user_id)
        else:
            await delete_data("tasks_for_scheduler", name="reminder_1day", user_id=user_id)

        user_subscribe = await get_data("user_subscriptions", user_id=user_id)
        if not user_subscribe:
            logger.warning(f"Пользователь {user_id} не найден в подписках при отправке напоминания")
            return
            
        datetime_end_subscribe = datetime.datetime.strptime(
            user_subscribe["datetime_end_subscribe"], "%Y-%m-%d %H:%M:%S.%f"
        ).strftime("%d.%m.%Y %H:%M")

        await dp.bot.send_message(
            chat_id=user_id,
            text=(
                "У вас заканчивается подписка!\n"
                f"⏳ Подписка <b>активна</b> и действует до <b>{datetime_end_subscribe}</b>"
            ),
            reply_markup=await get_keyboard(
                [[("Продлить", "about_subscribe"), ("Главное меню", "start")]]
            ),
        )
        logger.info(f"Напоминание успешно отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")


async def generate_invite_links(channel_id=None):
    """Генерирует пригласительные ссылки"""
    invite_links = []

    if channel_id:
        channel_list = [channel_id]
    else:
        channel_list = await get_data(
            "tracked_channels", "forward_channel_id", fetch="all"
        )

    for channel_id in channel_list:
        while True:  # Повторяем попытку до успеха
            try:
                invite_data = await dp.bot.create_chat_invite_link(
                    chat_id=channel_id,
                    member_limit=1,
                )
                invite_links.append(invite_data.invite_link)

                # Добавляем задержку между запросами и выходим из while, если успех
                await asyncio.sleep(0.1)
                break

            except utils.exceptions.RetryAfter as e:
                # Если поймали исключение RetryAfter, ждем указанное количество секунд
                await asyncio.sleep(e.timeout)
            except Exception as ex:
                # Отлавливаем неизвестную ошибку
                invite_links.append("empty")
                logging.error(
                    f"Не удалось создать пригласительную ссылку в {channel_id}\n"
                    f"Причина: {ex}"
                )
                break

    return invite_links


async def get_invite_links(sub_id):
    """Возвращает пригласительные ссылки"""
    result = []

    tracked_channels = await get_data("tracked_channels", fetch="all")

    for channel in tracked_channels:
        # Это полное говно
        link = await get_data(
            "user_links", f'"{channel["channel_id"]}"', user_id=sub_id
        )
        # Блять как же я хочу сделать жесткий рефактор тут всего это просто пиздец
        result.append((channel["title"], link))

    return await get_keyboard([result])


async def unban_user(user_id):
    """Разблокировка пользователей"""
    tracked_channels = await get_data(
        "tracked_channels", "forward_channel_id", fetch="all"
    )

    if not tracked_channels:
        return

    for chat_id in tracked_channels:
        try:
            await dp.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
        except Exception as ex:
            logging.error(
                f"Не удалось разбанить пользователя {user_id} в {chat_id}\n"
                f"Причина: {ex}"
            )
            continue

        await asyncio.sleep(0.05)


async def ban_user(user_id):
    """Бан пользователя"""
    logger.info(f"Бан пользователя {user_id} - истечение подписки")
    
    try:
        await delete_data("tasks_for_scheduler", name="end_subscribe", user_id=user_id)
        await delete_data("user_subscriptions", user_id=user_id)
        await delete_data("user_links", user_id=user_id)
        
        if user_id in ADMINS:
            logger.info(f"Пользователь {user_id} является админом, бан пропущен")
            return

        tracked_channels = await get_data(
            "tracked_channels", "forward_channel_id", fetch="all"
        )

        if not tracked_channels:
            logger.warning(f"Нет каналов для бана пользователя {user_id}")
            return

        banned_count = 0
        for chat_id in tracked_channels:
            try:
                await dp.bot.ban_chat_member(chat_id, user_id)
                banned_count += 1
            except Exception as ex:
                logger.error(
                    f"Не удалось забанить пользователя {user_id} в {chat_id}: {ex}"
                )
                continue
            await asyncio.sleep(0.05)
        
        logger.info(f"Пользователь {user_id} забанен в {banned_count}/{len(tracked_channels)} каналах")
    except Exception as e:
        logger.error(f"Ошибка при бане пользователя {user_id}: {e}")


async def send_invite_links(user_id):
    """Отправка пригласительных ссылок"""
    await dp.bot.send_message(
        chat_id=user_id,
        text=(
            "Важный дисклеймер: здесь нет индивидуальных инвестиционных "
            "рекомендаций (ИИР), всю информацию необходимо использовать с "
            "личной ответственностью."
        ),
        reply_markup=await get_invite_links(user_id),
    )

    await dp.bot.send_message(
        chat_id=user_id,
        text="Чтобы вернуться назад нажмите на кнопку <b>Начальный экран</b>",
        reply_markup=await get_keyboard([[("Начальный экран", "start")]]),
    )


async def give_subscription(user_id, days):
    """Обновление даты и времени окончания подписки"""
    logger.info(f"Выдача подписки пользователю {user_id} на {days} дней")
    
    try:
        await unban_user(user_id)

        await dp.bot.send_message(
            chat_id=user_id, text=(f"Вам выдана подписка на {days} дней")
        )
    except Exception as e:
        logger.error(f"Ошибка при выдаче подписки пользователю {user_id}: {e}")
        raise

    current_end_datetime = await get_data("user_subscriptions", user_id=user_id)
    duration_date = datetime.timedelta(days=days)
    # If first time sub -> create new
    if not current_end_datetime:
        links = await generate_invite_links()
        tracked_channels_ids = await get_data(
            "tracked_channels", "channel_id", fetch="all"
        )
        datetime_end_subscribe = datetime.datetime.now() + duration_date
        await add_new_data(
            "user_subscriptions",
            data=(user_id, datetime_end_subscribe),
        )
        await add_new_data(
            "user_links",
            data=[user_id] + links,
            keys=["user_id"] + [f'"{id}"' for id in tracked_channels_ids],
            start_index=0,
        )
    # Else -> change existing
    else:
        datetime_end_subscribe = (
            datetime.datetime.strptime(
                current_end_datetime["datetime_end_subscribe"], "%Y-%m-%d %H:%M:%S.%f"
            )
            + duration_date
        )
        await update_data(
            "user_subscriptions",
            set={"datetime_end_subscribe": (datetime_end_subscribe)},
            where={"id": current_end_datetime["id"]},
        )
        # I think it is not nesessary for known users

        # await delete_data(
        #     "user_links", user_id=user_id
        # )  # Так потому что я не знаю как с неопределенным количеством каналов работать
        # await add_new_data(
        #     "user_links",
        #     data=[user_id] + links,
        #     keys=["user_id"] + [f'"{id}"' for id in tracked_channels_ids],
        #     start_index=0,
        # )

    # Добавление удаления по расписанию
    await add_scheduler_task("end_subscribe", user_id, datetime_end_subscribe)
    # Добавление напоминания об окончании подписки 1 день
    await add_scheduler_task(
        "reminder_1day", user_id, datetime_end_subscribe - datetime.timedelta(days=1)
    )
    # Добавление напоминания об окончании подписки 3 дня
    await add_scheduler_task(
        "reminder_3days", user_id, datetime_end_subscribe - datetime.timedelta(days=3)
    )


async def add_scheduler_task(name, user_id, date):
    """Добавление задание в планировщик и бд"""
    if date < datetime.datetime.now():
        return

    job_id = f"{name}_{user_id}"
    try:
        await delete_data("tasks_for_scheduler", name=name, user_id=user_id)
        scheduler.remove_job(job_id)  # Удаление старого задания
    except:
        pass

    scheduler.add_job(  # Не будет работать если дата уже прошла
        func=ban_user if name == "end_subscribe" else reminder_user,
        trigger="date",
        run_date=date,
        args=[user_id],
        id=job_id,
    )
    await add_new_data(
        "tasks_for_scheduler",
        data=(
            user_id,
            date,
            name,
        ),
    )


async def get_number_with_spaces(number):
    """Возвращает число с разделителями"""
    return "<b>{0:,}</b>".format(number).replace(",", " ")


async def get_user_profile(user_id):
    """Возвращает профиль пользователя"""
    user_data = await get_data("users", user_id=user_id)
    if user_data["username"]:
        return f'@{user_data["username"]}'
    else:
        return f'<a href="tg://user?id={user_id}">{user_data["first_name"]}</a>'
