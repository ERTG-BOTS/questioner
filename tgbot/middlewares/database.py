import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import Config
from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, config: Config, bot: Bot, session_pool) -> None:
        self.session_pool = session_pool
        self.bot = bot
        self.config = config

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            repo: RequestsRepo = RequestsRepo(session)

            user: User = await repo.users.get_user(user_id=event.from_user.id)

            message_thread_id = None
            is_bot = False

            if isinstance(event, Message):
                # Обычное текстовое сообщение
                message_thread_id = event.message_thread_id
                is_bot = event.from_user.is_bot
            elif isinstance(event, CallbackQuery) and event.message:
                # CallbackQuery - проверяем оригинальное сообщение
                message_thread_id = getattr(event.message, "message_thread_id", None)
                is_bot = event.from_user.is_bot

            # Check if user exists
            if not user and message_thread_id and not is_bot:
                await self.bot.ban_chat_member(
                    chat_id=self.config.tg_bot.forum_id, user_id=event.from_user.id
                )
                await self.bot.send_message(
                    chat_id=self.config.tg_bot.forum_id,
                    text=f"""<b>Блокировка</b>

Пользователь с id {event.from_user.id} не найден в базе""",
                )
                return

            # Check user role for forum access
            if (
                user
                and user.Role not in [2, 3, 10]
                and message_thread_id
                and not is_bot
            ):
                await self.bot.ban_chat_member(
                    chat_id=self.config.tg_bot.forum_id, user_id=event.from_user.id
                )
                await self.bot.send_message(
                    chat_id=self.config.tg_bot.forum_id,
                    text=f"""<b>Блокировка</b>

Пользователь имеет роль {user.Role}, для доступа нужна одна из следующих ролей: 2, 3, 10""",
                )
                return

            # NEW: Check user division for private messages
            if user and not message_thread_id and not is_bot:
                if self.config.tg_bot.division not in user.Division:
                    if "НТП" in user.Division:
                        correct_bot_link = "https://t.me/ntp2question_bot"
                    else:
                        correct_bot_link = "https://t.me/NCKQuestionBot"

                    await self.bot.send_message(
                        chat_id=event.from_user.id,
                        text=f"Текущий бот работает только для <b>{self.config.tg_bot.division}</b>. Перейди в <a href='{correct_bot_link}'>своего бота</a>"
                    )
                    logger.warning(
                        f"[Доступ] Пользователь {event.from_user.username} ({event.from_user.id}) из {user.Division} попытался использовать бот для {self.config.tg_bot.division}"
                    )
                    return

            data["session"] = session
            data["repo"] = repo
            data["user"] = user

            result = await handler(event, data)
        return result