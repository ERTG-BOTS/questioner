import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import DisconnectionError, OperationalError, DBAPIError

from infrastructure.database.models import Question, User
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
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                async with self.session_pool() as session:
                    repo: RequestsRepo = RequestsRepo(session)

                    user: User = await repo.users.get_user(user_id=event.from_user.id)

                    message_thread_id = None
                    is_bot = False

                    if isinstance(event, Message):
                        # Handle both regular messages and edited messages
                        message_thread_id = event.message_thread_id
                        is_bot = event.from_user.is_bot

                        # Log if this is an edited message
                        if hasattr(event, "edit_date") and event.edit_date:
                            logger.info(
                                f"[Редактирование] Пользователь {event.from_user.username} ({event.from_user.id}) "
                                f"отредактировал сообщение в топике {message_thread_id}"
                            )

                    elif isinstance(event, CallbackQuery) and event.message:
                        # CallbackQuery - проверяем оригинальное сообщение
                        message_thread_id = getattr(
                            event.message, "message_thread_id", None
                        )
                        is_bot = event.from_user.is_bot

                    # Проверка на существования пользователя
                    if not user and message_thread_id and not is_bot:
                        await self.bot.ban_chat_member(
                            chat_id=self.config.tg_bot.forum_id,
                            user_id=event.from_user.id,
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
                            chat_id=self.config.tg_bot.forum_id,
                            user_id=event.from_user.id,
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
                                    logger.error(
                                        f"[Доступ] Не удалось ответить в топике: {e}"
                                    )

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

                    question: Question = None
                    active_dialog_token: str = None

                    # Сперва пробуем получить вопрос из топика (для сообщений в топиках)
                    if message_thread_id and message_thread_id != 1:
                        try:
                            question = await repo.questions.get_question(
                                topic_id=message_thread_id
                            )
                            if question:
                                logger.debug(
                                    f"[Вопрос] Загружен вопрос {question.Token} для топика {message_thread_id}"
                                )
                        except (OperationalError, DBAPIError, DisconnectionError) as e:
                            # Handle specific database connection errors
                            if "Connection is busy" in str(e) or "HY000" in str(e):
                                logger.warning(
                                    f"[Вопрос] Connection busy для топика {message_thread_id}, повтор {retry_count + 1}/{max_retries}: {e}"
                                )
                                retry_count += 1
                                if retry_count < max_retries:
                                    continue  # Retry the entire middleware
                                else:
                                    logger.error(
                                        f"[Вопрос] Все попытки исчерпаны для топика {message_thread_id}: {e}"
                                    )
                                    # Continue without the question data
                                    question = None
                            else:
                                # For other database errors, don't retry
                                logger.error(
                                    f"[Вопрос] Ошибка БД при загрузке вопроса для топика {message_thread_id}: {e}"
                                )
                                question = None

                    # Если нет вопроса для топика, пытаемся получить активные вопросы специалиста (для личных сообщений)
                    elif user and not message_thread_id and not is_bot:
                        try:
                            from sqlalchemy import Sequence

                            current_dialogs: Sequence[
                                Question
                            ] = await repo.questions.get_active_questions()

                            for dialog in current_dialogs:
                                if dialog.EmployeeChatId == event.from_user.id:
                                    question = dialog
                                    active_dialog_token = dialog.Token
                                    logger.debug(
                                        f"[Вопрос] Автоматически загружен активный вопрос {question.Token} для пользователя {event.from_user.id}"
                                    )
                                    break
                        except (OperationalError, DBAPIError, DisconnectionError) as e:
                            if "Connection is busy" in str(e) or "HY000" in str(e):
                                logger.warning(
                                    f"[Вопрос] Connection busy для активных вопросов пользователя {event.from_user.id}, повтор {retry_count + 1}/{max_retries}: {e}"
                                )
                                retry_count += 1
                                if retry_count < max_retries:
                                    continue  # Retry the entire middleware
                                else:
                                    logger.error(
                                        f"[Вопрос] Все попытки исчерпаны для активных вопросов пользователя {event.from_user.id}: {e}"
                                    )
                                    # Continue without the question data
                                    question = None
                                    active_dialog_token = None
                            else:
                                logger.error(
                                    f"[Вопрос] Ошибка БД при загрузке активного вопроса пользователя {event.from_user.id}: {e}"
                                )
                                question = None
                                active_dialog_token = None

                    data["session"] = session
                    data["repo"] = repo
                    data["user"] = user
                    data["question"] = question
                    data["active_dialog_token"] = active_dialog_token

                    result = await handler(event, data)
                    return result

            except (OperationalError, DBAPIError, DisconnectionError) as e:
                if "Connection is busy" in str(e) or "HY000" in str(e):
                    retry_count += 1
                    logger.warning(
                        f"[Middleware] Database connection error, повтор {retry_count}/{max_retries}: {e}"
                    )
                    if retry_count >= max_retries:
                        logger.error(
                            f"[Middleware] Все попытки подключения к БД исчерпаны: {e}"
                        )
                        # You might want to send an error message to the user here
                        if isinstance(event, Message):
                            try:
                                await event.reply(
                                    "⚠️ Временные проблемы с базой данных. Попробуйте позже."
                                )
                            except:
                                pass  # Ignore if we can't send the error message
                        return None
                else:
                    # For other database errors, don't retry
                    logger.error(f"[Middleware] Критическая ошибка БД: {e}")
                    return None
            except Exception as e:
                logger.error(f"[Middleware] Неожиданная ошибка: {e}")
                return None

        return None
