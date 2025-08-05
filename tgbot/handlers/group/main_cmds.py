import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.topic import IsMainTopicMessageWithCommand
from tgbot.services.logger import setup_logging

main_topic_cmds_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@main_topic_cmds_router.message(IsMainTopicMessageWithCommand("link"))
async def link_cmd(message: Message):
    group_link = await message.bot.export_chat_invite_link(chat_id=message.chat.id)
    await message.reply(
        f"Пригласительная ссылка на этот чат:\n<code>{group_link}</code>"
    )


@main_topic_cmds_router.message(IsMainTopicMessageWithCommand("settings"))
async def settings_cmd(message: Message, questions_repo: RequestsRepo):
    group_settings = await questions_repo.settings.get_settings_by_group_id(
        group_id=message.chat.id,
    )

    await message.reply(
        f"""⚙️ Настройки <b>{message.chat.title}</b>

<b>🧩 Функции:</b>
- Запрос регламента - {"Да" if group_settings.get_setting("ask_clever_link") else "Нет"} (/clever)
- Закрытие по бездействию - {"Да" if group_settings.get_setting("activity_status") else "Нет"} (/activity)

<b>⏳ Таймеры:</b>
- Предупреждение о бездействии - {group_settings.get_setting("activity_warn_minutes")} минут (/warn)
- Закрытие по бездействию - {group_settings.get_setting("activity_close_minutes")} минут (/close)
"""
    )


@main_topic_cmds_router.message(Command("clever"), IsMainTopicMessageWithCommand())
async def ask_clever_link_change(
    message: Message, command: CommandObject, user: User, questions_repo: RequestsRepo
):
    """Управление статусом запроса регламента для форумов."""
    if user.Role not in [2, 10]:
        await message.reply(
            "Доступ к изменению настроек форума есть только у РГ и администраторов 🥺"
        )
        return

    # Валидация аргументов команды
    if not command.args:
        await message.reply("Пример команды: /clever [on или off]")
        return

    action = command.args.split(maxsplit=1)[0].lower()
    if action not in ("on", "off"):
        await message.reply("Пример команды: /clever [on или off]")
        return

    # Получаем текущие настройки
    group_settings = await questions_repo.settings.get_settings_by_group_id(
        group_id=message.chat.id
    )

    current_state = group_settings.get_setting("ask_clever_link")
    target_state = action == "on"
    user_name = user.FIO

    # Определяем ответ в зависимости от текущего состояния настройки и нового состояния
    if current_state == target_state:
        status = "включен" if current_state else "выключен"
        response = (
            f"<b>✨ Изменение настроек форума</b>\n\n"
            f"Запрос регламента <b>уже {status}</b>"
        )
    else:
        # Обновление настроек
        await questions_repo.settings.update_setting(
            group_id=message.chat.id, key="ask_clever_link", value=target_state
        )
        action_text = "включил" if target_state else "выключил"
        response = (
            f"<b>✨ Изменение настроек форума</b>\n\n"
            f"Пользователь <b>{user_name}</b> {action_text} запрос регламента"
        )

    await message.reply(response)


@main_topic_cmds_router.message(Command("activity"), IsMainTopicMessageWithCommand())
async def activity_change(
    message: Message, command: CommandObject, user: User, questions_repo: RequestsRepo
):
    """Управление статусом закрытия по бездействию."""
    if user.Role not in [2, 10]:
        await message.reply(
            "Доступ к изменению настроек форума есть только у РГ и администраторов 🥺"
        )
        return

    # Валидация аргументов команды
    if not command.args:
        await message.reply("Пример команды: /activity [on или off]")
        return

    action = command.args.split(maxsplit=1)[0].lower()
    if action not in ("on", "off"):
        await message.reply("Пример команды: /activity [on или off]")
        return

    # Получаем текущие настройки
    group_settings = await questions_repo.settings.get_settings_by_group_id(
        group_id=message.chat.id
    )

    current_state = group_settings.get_setting("activity_status")
    target_state = action == "on"
    user_name = user.FIO

    # Определяем ответ в зависимости от текущего состояния настройки и нового состояния
    if current_state == target_state:
        status = "включено" if current_state else "выключено"
        response = (
            f"<b>✨ Изменение настроек форума</b>\n\n"
            f"Закрытие по бездействию <b>уже {status}</b>"
        )
    else:
        # Обновление настроек
        await questions_repo.settings.update_setting(
            group_id=message.chat.id, key="activity_status", value=target_state
        )
        action_text = "включил" if target_state else "выключил"
        response = (
            f"<b>✨ Изменение настроек форума</b>\n\n"
            f"Пользователь <b>{user_name}</b> {action_text} закрытие по бездействию"
        )

    await message.reply(response)


@main_topic_cmds_router.message(Command("warn"), IsMainTopicMessageWithCommand())
async def timer_warn_change(
    message: Message, command: CommandObject, user: User, questions_repo: RequestsRepo
):
    """Управление временем предупреждения о закрытии по бездействию."""
    if user.Role not in [2, 10]:
        await message.reply(
            "Доступ к изменению настроек форума есть только у РГ и администраторов 🥺"
        )
        return

    # Валидация аргументов команды
    if not command.args:
        await message.reply("Пример команды: /warn [время в минутах]")
        return

    new_timer = command.args.split(maxsplit=1)[0]
    if type(int(new_timer)) is not int:
        await message.reply("Пример команды: /warn [время в минутах]")
        return

    # Получаем текущие настройки
    group_settings = await questions_repo.settings.get_settings_by_group_id(
        group_id=message.chat.id
    )

    current_state = int(group_settings.get_setting("activity_warn_minutes"))
    close_state = int(group_settings.get_setting("activity_close_minutes"))
    user_name = user.FIO

    # Определяем ответ в зависимости от текущего состояния настройки и нового состояния
    if current_state == new_timer:
        response = (
            f"<b>✨ Изменение настроек форума</b>\n\n"
            f"Предупреждение <b>уже через {new_timer} минут</b>"
        )
    else:
        if int(new_timer) < close_state:
            # Обновление настроек
            await questions_repo.settings.update_setting(
                group_id=message.chat.id, key="activity_warn_minutes", value=new_timer
            )
            response = (
                f"<b>✨ Изменение настроек форума</b>\n\n"
                f"Пользователь <b>{user_name}</b> установил предупреждение через {new_timer} минут"
            )
        else:
            response = (
                f"<b>✨ Изменение настроек форума</b>\n\n"
                f"Невозможно установить время предупреждения меньше или равному времени закрытия ({close_state} минут) "
            )

    await message.reply(response)


@main_topic_cmds_router.message(Command("close"), IsMainTopicMessageWithCommand())
async def timer_close_change(
    message: Message, command: CommandObject, user: User, questions_repo: RequestsRepo
):
    """Управление временем закрытия по бездействию."""
    if user.Role not in [2, 10]:
        await message.reply(
            "Доступ к изменению настроек форума есть только у РГ и администраторов 🥺"
        )
        return

    # Валидация аргументов команды
    if not command.args:
        await message.reply("Пример команды: /close [время в минутах]")
        return

    new_timer = command.args.split(maxsplit=1)[0]
    if type(int(new_timer)) is not int:
        await message.reply("Пример команды: /close [время в минутах]")
        return

    # Получаем текущие настройки
    group_settings = await questions_repo.settings.get_settings_by_group_id(
        group_id=message.chat.id
    )

    current_state = int(group_settings.get_setting("activity_close_minutes"))
    warn_state = int(group_settings.get_setting("activity_warn_minutes"))
    target_state = new_timer == current_state
    user_name = user.FIO

    # Определяем ответ в зависимости от текущего состояния настройки и нового состояния
    if current_state == target_state:
        response = (
            f"<b>✨ Изменение настроек форума</b>\n\n"
            f"Закрытие <b>уже {new_timer} минут</b>"
        )
    else:
        if int(new_timer) > warn_state:
            # Обновление настроек
            await questions_repo.settings.update_setting(
                group_id=message.chat.id, key="activity_close_minutes", value=new_timer
            )
            response = (
                f"<b>✨ Изменение настроек форума</b>\n\n"
                f"Пользователь <b>{user_name}</b> установил таймер закрытия на {new_timer} минут"
            )
        else:
            response = (
                f"<b>✨ Изменение настроек форума</b>\n\n"
                f"Невозможно установить время закрытия меньше или равному времени предупреждения ({warn_state} минут) "
            )

    await message.reply(response)
