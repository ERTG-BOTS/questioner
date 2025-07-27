import logging
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import DBAPIError, DisconnectionError, OperationalError

from infrastructure.database.models import Question, User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import Config, load_config
from tgbot.keyboards.group.events import on_user_leave_kb
from tgbot.services.logger import setup_logging

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    def __init__(
        self, config: Config, bot: Bot, main_session_pool, questioner_session_pool
    ) -> None:
        self.main_session_pool = main_session_pool
        self.questioner_session_pool = questioner_session_pool
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
                # Use separate sessions for different databases
                async with self.main_session_pool() as main_session:
                    async with self.questioner_session_pool() as questioner_session:
                        # Создаем репозитории для разных БД
                        main_repo = RequestsRepo(main_session)  # Для БД STPMain
                        questioner_repo = RequestsRepo(
                            questioner_session
                        )  # Для БД QuestionerBot

                        user: User = await main_repo.users.get_user(
                            user_id=event.from_user.id
                        )

                        message_thread_id = None
                        is_bot = False

                        if isinstance(event, Message):
                            message_thread_id = event.message_thread_id
                            is_bot = event.from_user.is_bot

                            if hasattr(event, "edit_date") and event.edit_date:
                                logger.info(
                                    f"[Редактирование] Пользователь {event.from_user.username} ({event.from_user.id}) "
                                    f"отредактировал сообщение в топике {message_thread_id}"
                                )

                        elif isinstance(event, CallbackQuery) and event.message:
                            message_thread_id = getattr(
                                event.message, "message_thread_id", None
                            )
                            is_bot = event.from_user.is_bot

                        # User validation logic remains the same...
                        if not user and not is_bot:
                            await self.bot.ban_chat_member(
                                chat_id=self.config.tg_bot.ntp_forum_id
                                if "НТП" in user.Division
                                else config.tg_bot.nck_forum_id,
                                user_id=event.from_user.id,
                            )
                            await event.answer(
                                text=f"""<b>🙅‍♂️ Исключение</b>

Пользователь <code>{event.from_user.id}</code> исключен
Причина: не найден в базе""",
                                reply_markup=on_user_leave_kb(
                                    user_id=event.from_user.id,
                                ),
                            )
                            return

                        if (
                            user
                            and user.Role not in [2, 3, 10]
                            and message_thread_id
                            and not is_bot
                        ):
                            await self.bot.ban_chat_member(
                                chat_id=self.config.tg_bot.ntp_forum_id
                                if "НТП" in user.Division
                                else config.tg_bot.nck_forum_id,
                                user_id=event.from_user.id,
                            )
                            await event.answer(
                                text=f"""<b>🙅‍♂️ Исключение</b>

Пользователь <code>{event.from_user.id}</code> исключен
Причина: недостаточно прав для входа""",
                                reply_markup=on_user_leave_kb(
                                    user_id=event.from_user.id, change_role=True
                                ),
                            )
                            return

                        question: Question = None
                        active_question_token: str = None

                        # Get question from questioner database
                        if message_thread_id and message_thread_id != 1 and user:
                            try:
                                question = await questioner_repo.questions.get_question(
                                    topic_id=message_thread_id,
                                    group_id=config.tg_bot.ntp_forum_id
                                    if "НТП" in user.Division
                                    else config.tg_bot.nck_forum_id,
                                )
                                if question:
                                    logger.debug(
                                        f"[Вопрос] Загружен вопрос {question.token} для топика {message_thread_id}"
                                    )
                                else:
                                    await event.reply(
                                        text="""<b>🙅‍♂️ Ошибка</b>

Запрещено отвечать на вопросы чужого направления""",
                                    )
                                    logger.error(
                                        f"[Вопрос] Не удалось загрузить вопрос в топике {message_thread_id} и группе {'НТП' if config.tg_bot.ntp_forum_id == event.chat.id else 'НЦК'}"
                                    )
                            except (
                                OperationalError,
                                DBAPIError,
                                DisconnectionError,
                            ) as e:
                                if "Connection is busy" in str(e) or "HY000" in str(e):
                                    logger.warning(
                                        f"[Вопрос] Connection busy для топика {message_thread_id}, повтор {retry_count + 1}/{max_retries}: {e}"
                                    )
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        continue
                                    else:
                                        logger.error(
                                            f"[Вопрос] Все попытки исчерпаны для топика {message_thread_id}: {e}"
                                        )
                                        question = None
                                else:
                                    logger.error(
                                        f"[Вопрос] Ошибка БД при загрузке вопроса для топика {message_thread_id}: {e}"
                                    )
                                    question = None

                        elif user and not message_thread_id and not is_bot:
                            try:
                                active_questions = await questioner_repo.questions.get_active_questions()

                                for question in active_questions:
                                    if question.employee_chat_id == event.from_user.id:
                                        question = question
                                        active_question_token = question.token
                                        logger.debug(
                                            f"[Вопрос] Автоматически загружен активный вопрос {question.token} для пользователя {event.from_user.id}"
                                        )
                                        break
                            except (
                                OperationalError,
                                DBAPIError,
                                DisconnectionError,
                            ) as e:
                                if "Connection is busy" in str(e) or "HY000" in str(e):
                                    retry_count += 1
                                    if retry_count < max_retries:
                                        continue
                                    else:
                                        question = None
                                        active_question_token = None
                                else:
                                    question = None
                                    active_question_token = None

                        data["main_session"] = main_session
                        data["questioner_session"] = questioner_session
                        data["questions_repo"] = questioner_repo
                        data["main_repo"] = main_repo
                        data["user"] = user
                        data["question"] = question
                        data["active_question_token"] = active_question_token

                        result = await handler(event, data)
                        return result

            except (OperationalError, DBAPIError, DisconnectionError) as e:
                # Retry logic...
                if "Connection is busy" in str(e) or "HY000" in str(e):
                    retry_count += 1
                    logger.warning(
                        f"[Middleware] Database connection error, повтор {retry_count}/{max_retries}: {e}"
                    )
                    if retry_count >= max_retries:
                        logger.error(
                            f"[Middleware] Все попытки подключения к БД исчерпаны: {e}"
                        )
                        if isinstance(event, Message):
                            try:
                                await event.reply(
                                    "⚠️ Временные проблемы с базой данных. Попробуйте позже."
                                )
                            except:
                                pass
                        return None
                else:
                    logger.error(f"[Middleware] Критическая ошибка БД: {e}")
                    return None
            except Exception as e:
                logger.error(f"[Middleware] Неожиданная ошибка: {e}")
                return None

        return None
