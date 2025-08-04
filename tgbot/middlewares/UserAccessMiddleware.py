import logging
from typing import Any, Awaitable, Callable, Dict, Sequence, Union

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Question, User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.group.events import on_user_leave_kb
from tgbot.misc import dicts
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

        # Skip all access control logic for private chats, bots, or if no chat found
        if not chat or chat.type == "private" or event.from_user.is_bot:
            return await handler(event, data)

        # Get user and repos from previous middleware (DatabaseMiddleware)
        user: User = data.get("user")
        questions_repo: RequestsRepo = data.get("questions_repo")

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
                f"[Edit] User {event.from_user.username} ({event.from_user.id}) "
                f"edited message in topic {message_thread_id}"
            )

        # Check if user exists in database
        if not user:
            if message_thread_id:
                await self._ban_user_with_notification(
                    event,
                    chat,
                    f"User <code>{event.from_user.id}</code> banned\nReason: not found in database",
                )
            return None

        # Check if user has sufficient permissions for topic access
        if user.Role not in [2, 3, 10] and message_thread_id:
            await self._ban_user_with_notification(
                event,
                chat,
                f"User <code>{user.FIO}</code> banned\nReason: insufficient permissions for access",
                change_role=True,
            )

            # Handle active questions for banned user
            await self._handle_banned_user_questions(user, questions_repo, chat.id)
            return None

        # User passed all checks, continue to next middleware/handler
        return await handler(event, data)

    def _get_message_thread_id(self, event: Union[Message, CallbackQuery]) -> int:
        """Extract message_thread_id from event"""
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
        """Ban user and send notification"""
        await self.bot.ban_chat_member(
            chat_id=chat.id,
            user_id=event.from_user.id,
        )

        # Send notification message
        if isinstance(event, Message):
            await event.answer(
                text=f"<b>🙅‍♂️ Exclusion</b>\n\n{message}",
                reply_markup=on_user_leave_kb(
                    user_id=event.from_user.id, change_role=change_role
                ),
            )
        else:
            await self.bot.send_message(
                chat_id=chat.id,
                text=f"<b>🙅‍♂️ Exclusion</b>\n\n{message}",
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

        # Find questions assigned to banned user
        duty_active_questions = [
            question
            for question in active_questions
            if user.FIO == question.topic_duty_fullname
        ]

        if not duty_active_questions:
            return

        # Release all questions assigned to banned user
        for question in duty_active_questions:
            await questions_repo.questions.update_question(
                token=question.token,
                topic_duty_fullname=None,
                status="open",
            )

            # Update topic emoji
            await self.bot.edit_forum_topic(
                chat_id=question.group_id,
                message_thread_id=question.topic_id,
                icon_custom_emoji_id=dicts.topicEmojis["open"],
            )

            # Notify in topic
            await self.bot.send_message(
                chat_id=question.group_id,
                message_thread_id=question.topic_id,
                text=f"""<b>🕊️ Question Released</b>

Duty officer <b>{user.FIO}</b> was excluded due to insufficient permissions
To take the question, write a message in this topic""",
            )

            # Notify employee
            await self.bot.send_message(
                chat_id=question.employee_chat_id,
                text=f"""<b>🕊️ Duty Officer Left Chat</b>

Duty officer <b>{user.FIO}</b> released the question. Wait for senior reconnection""",
            )

            logger.info(
                f"[Question] - [Release] Duty officer {user.FIO} ({user.ChatId}) "
                f"excluded and released from question {question.token}"
            )

        # Send summary of released questions
        question_list = []
        for i, question in enumerate(duty_active_questions, 1):
            link = f"<a href='https://t.me/c/{str(question.group_id)[4:]}/{question.topic_id}'>{str(question.token)}</a>"
            question_list.append(f"{i}. {link}")

        question_text = "\n".join(question_list) if question_list else "No questions"

        await self.bot.send_message(
            chat_id=chat_id,
            text=f"List of questions with excluded duty officer:\n{question_text}",
        )
