import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message

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
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            repo: RequestsRepo = RequestsRepo(session)

            user: User = await repo.users.get_user(
                user_id=event.from_user.id
            )

            if not user and event.message_thread_id and not event.from_user.is_bot:
                await self.bot.ban_chat_member(chat_id=self.config.tg_bot.forum_id, user_id=event.from_user.id)
                await self.bot.send_message(chat_id=self.config.tg_bot.forum_id, text=f"""<b>Блокировка</b>

Пользователь с id {event.from_user.id} не найден в базе""")
            elif user and user.Role not in [2, 3, 10] and event.message_thread_id and not event.from_user.is_bot:
                await self.bot.ban_chat_member(chat_id=self.config.tg_bot.forum_id, user_id=event.from_user.id)
                await self.bot.send_message(chat_id=self.config.tg_bot.forum_id, text=f"""<b>Блокировка</b>

Пользователь имеет роль {user.Role}, для доступа нужна одна из следующих ролей: 2, 3, 10""")

            data["session"] = session
            data["repo"] = repo
            data["user"] = user

            result = await handler(event, data)
        return result