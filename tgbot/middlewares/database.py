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

            # Проверка на существования пользователя
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

            # Проверка роли пользователя для доступа к группе
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

            # Проверка направления пользователя для всех взаимодействий (кроме ботов)
            if user and not is_bot:
                if self.config.tg_bot.division not in user.Division:
                    # Определяем ссылки в зависимости от направления пользователя
                    if "НТП" in user.Division:
                        bot_link = "https://t.me/ntp2question_bot"
                        group_link = "https://t.me/+roCjjAKZk8NhYjQy"
                    else:
                        bot_link = "https://t.me/NCKQuestionBot"
                        group_link = "https://t.me/+FJhHF8qbGJkzY2Iy"

                    # Если это сообщение - отправляем предупреждение в лс
                    try:
                        await self.bot.send_message(
                            chat_id=event.from_user.id,
                            text=f"Текущий бот работает только для <b>{self.config.tg_bot.division}</b>. Перейди в <a href='{bot_link}'>своего бота</a>",
                            disable_web_page_preview=True,
                        )
                    except Exception as e:
                        logger.error(
                            f"[Доступ] Не удалось отправить сообщение пользователю {event.from_user.id}: {e}"
                        )

                    # Если это топик - отправляем предложение перейти в группу своего направления
                    if message_thread_id and isinstance(event, Message):
                        try:
                            await event.reply(
                                f"<b>⚠️ Неверное направление</b>\n\nДанный бот работает только для <b>{self.config.tg_bot.division}</b>. Перейди в <a href='{group_link}'>свою группу</a>",
                                disable_web_page_preview=True,
                            )
                        except Exception as e:
                            logger.error(f"[Доступ] Не удалось ответить в топике: {e}")

                    # Если это callback - отвечаем на него
                    if isinstance(event, CallbackQuery):
                        try:
                            await event.answer(
                                f"Данный бот работает только для {self.config.tg_bot.division}. Перейди в своего бота",
                                show_alert=True,
                            )
                        except Exception as e:
                            logger.error(
                                f"[Доступ] Не удалось ответить на callback: {e}"
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