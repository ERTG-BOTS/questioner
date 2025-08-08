import logging
from typing import Any, Awaitable, Callable, Dict, Sequence, Union

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Question, User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.group.events import on_user_leave_kb
from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class UserAccessMiddleware(BaseMiddleware):
    """
    Middleware responsible for user access control and banning logic.
    Checks if user exists in database and has sufficient permissions.
    """

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def __call__(
        self,
        handler: Callable[
            [Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]
        ],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        # Get chat from event (different for Message vs CallbackQuery)
        chat = (
            event.chat
            if isinstance(event, Message)
            else event.message.chat
            if event.message
            else None
        )

        # Get user and repos from previous middleware (DatabaseMiddleware)
        user: User = data.get("user")
        main_repo: RequestsRepo = data.get("main_repo")
        questions_repo: RequestsRepo = data.get("questions_repo")

        # Skip all access control logic for private chats, bots, or if no chat found
        if not chat or chat.type == "private" or event.from_user.is_bot:
            # Проверяем необходимость обновления пользователя
            await self._update_username(user, event, main_repo)

            return await handler(event, data)

        if not questions_repo:
            logger.error("[UserAccessMiddleware] No questions_repo found in data")
            return None

        # Extract common event properties
        message_thread_id = self._get_message_thread_id(event)

        # Log message edits
        if (
            isinstance(event, Message)
            and hasattr(event, "edit_date")
            and event.edit_date
        ):
            logger.info(
                f"[Изменение] Пользователь {event.from_user.username} ({event.from_user.id}) "
                f"изменил сообщение в топике {message_thread_id}"
            )

        # Проверяем есть ли пользователь в базе
        if not user:
            if message_thread_id:
                await self._ban_user_with_notification(
                    event,
                    chat,
                    f"Пользователь <code>{event.from_user.id}</code> заблокирован\nПричина: не найден в базе",
                )
            return None

        # Проверяем есть ли у пользователя доступ к форуму
        if user.Role not in [2, 3, 10] and message_thread_id:
            await self._ban_user_with_notification(
                event,
                chat,
                f"Пользователь <code>{user.FIO}</code> заблокирован\nПричина: недостаточно прав для доступа к чату",
                change_role=True,
            )

            # Обрабатываем активные вопросы заблокированного пользователя
            await self._handle_banned_user_questions(user, questions_repo, chat.id)
            return None

        # Юзер прошел все проверки - продолжаем к следующей middleware
        return await handler(event, data)

    def _get_message_thread_id(self, event: Union[Message, CallbackQuery]) -> int:
        """Экстракт message_thread_id из ивента"""
        if isinstance(event, Message):
            return event.message_thread_id
        elif isinstance(event, CallbackQuery) and event.message:
            return getattr(event.message, "message_thread_id", None)
        return None

    async def _ban_user_with_notification(
        self,
        event: Union[Message, CallbackQuery],
        chat,
        message: str,
        change_role: bool = False,
    ):
        """
        Бан пользователя с уведомлением
        """
        await self.bot.ban_chat_member(
            chat_id=chat.id,
            user_id=event.from_user.id,
        )

        # Отправка уведомления об исключении
        if isinstance(event, Message):
            await event.answer(
                text=f"<b>🙅‍♂️ Исключение</b>\n\n{message}",
                reply_markup=on_user_leave_kb(
                    user_id=event.from_user.id, change_role=change_role
                ),
            )
        else:
            await self.bot.send_message(
                chat_id=chat.id,
                text=f"<b>🙅‍♂️ Исключение</b>\n\n{message}",
                reply_markup=on_user_leave_kb(
                    user_id=event.from_user.id, change_role=change_role
                ),
            )

    async def _handle_banned_user_questions(
        self, user: User, questions_repo: RequestsRepo, chat_id: int
    ):
        """Handle active questions when user is banned"""
        active_questions: Sequence[
            Question
        ] = await questions_repo.questions.get_active_questions()

        # Находим активные вопросы пользователя
        duty_active_questions = [
            question
            for question in active_questions
            if user.FIO == question.topic_duty_fullname
        ]

        if not duty_active_questions:
            return

        # Освобождение всех вопросов, принадлежавших исключенному пользователю
        for question in duty_active_questions:
            group_settings = await questions_repo.settings.get_settings_by_group_id(
                group_id=question.group_id,
            )

            await questions_repo.questions.update_question(
                token=question.token,
                topic_duty_fullname=None,
                status="open",
            )

            # Обновление эмодзи топика
            await self.bot.edit_forum_topic(
                chat_id=question.group_id,
                message_thread_id=question.topic_id,
                icon_custom_emoji_id=group_settings.get_setting("emoji_open"),
            )

            # Уведомление в главную тему
            await self.bot.send_message(
                chat_id=question.group_id,
                message_thread_id=question.topic_id,
                text=f"""<b>🕊️ Вопрос освобожден</b>

Дежурный <b>{user.FIO}</b> был исключен из-за недостатка прав
Для взятия вопроса в работу напиши сообщение в эту тему""",
            )

            # Уведомление специалиста
            await self.bot.send_message(
                chat_id=question.employee_chat_id,
                text=f"""<b>🕊️ Вопрос освобожден</b>

Дежурный <b>{user.FIO}</b> освободил вопрос. Ожидай повторного подключения старшего""",
            )

            logger.info(
                f"[Вопрос] - [Освобождение] Дежурный {user.FIO} ({user.ChatId}) "
                f"исключен и освободил вопрос {question.token}"
            )

        # Send summary of released questions
        question_list = []
        for i, question in enumerate(duty_active_questions, 1):
            link = f"<a href='https://t.me/c/{str(question.group_id)[4:]}/{question.topic_id}'>{str(question.token)}</a>"
            question_list.append(f"{i}. {link}")

        question_text = "\n".join(question_list) if question_list else "Нет вопросов"

        await self.bot.send_message(
            chat_id=chat_id,
            text=f"Список активных вопросов исключенного дежурного:\n{question_text}",
        )

    async def _update_username(
        self, user: User, event: Union[Message, CallbackQuery], main_repo: RequestsRepo
    ):
        """
        Обновление юзернейма пользователя если он отличается от записанного
        :param user:
        :param event:
        :param main_repo:
        :return:
        """
        current_username = event.from_user.username
        stored_username = user.Username

        if stored_username != current_username:
            try:
                if current_username is None:
                    await main_repo.users.update_user(
                        user_id=event.from_user.id,
                        Username=None,
                    )
                    logger.info(
                        f"[Юзернейм] Удален юзернейм пользователя {event.from_user.id}"
                    )
                else:
                    await main_repo.users.update_user(
                        user_id=event.from_user.id, Username=current_username
                    )
                    logger.info(
                        f"[Юзернейм] Обновлен юзернейм пользователя {event.from_user.id} - @{current_username}"
                    )
            except Exception as e:
                logger.error(
                    f"[Юзернейм] Ошибка обновления юзернейма для пользователя {event.from_user.id}: {e}"
                )
