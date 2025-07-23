from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import QuestionConnection


class QuestionsConnectionsRepo:
    """Repository for managing message connections between user chats and forum topics"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_connection(
        self,
        user_chat_id: int,
        user_message_id: int,
        topic_chat_id: int,
        topic_message_id: int,
        topic_thread_id: Optional[int],
        question_token: str,
        direction: str,
    ) -> QuestionConnection:
        """
        Add a new message connection between user chat and forum topic

        Args:
            user_chat_id: User chat ID
            user_message_id: Message ID in user chat
            topic_chat_id: Forum chat ID
            topic_message_id: Message ID in forum topic
            topic_thread_id: Thread ID in forum topic (optional)
            question_token: Associated question token
            direction: 'user_to_topic' or 'topic_to_user'

        Returns:
            Created MessageConnection instance
        """
        connection = QuestionConnection(
            user_chat_id=user_chat_id,
            user_message_id=user_message_id,
            topic_chat_id=topic_chat_id,
            topic_message_id=topic_message_id,
            topic_thread_id=topic_thread_id,
            question_token=question_token,
            direction=direction,
        )

        self.session.add(connection)
        await self.session.commit()
        await self.session.flush()
        await self.session.refresh(connection)
        return connection

    async def find_by_user_message(
        self, user_chat_id: int, user_message_id: int
    ) -> Optional[QuestionConnection]:
        """Find connection by user chat message"""
        stmt = select(QuestionConnection).where(
            and_(
                QuestionConnection.user_chat_id == user_chat_id,
                QuestionConnection.user_message_id == user_message_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_topic_message(
        self, topic_chat_id: int, topic_message_id: int
    ) -> Optional[QuestionConnection]:
        """Find connection by topic message"""
        stmt = select(QuestionConnection).where(
            and_(
                QuestionConnection.topic_chat_id == topic_chat_id,
                QuestionConnection.topic_message_id == topic_message_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_pair_for_edit(
        self, chat_id: int, message_id: int
    ) -> Optional[QuestionConnection]:
        """
        Find the corresponding message pair for editing

        Args:
            chat_id: Chat ID of the message being edited
            message_id: Message ID being edited

        Returns:
            MessageConnection if found, None otherwise
        """
        # Try to find by user message
        connection = await self.find_by_user_message(chat_id, message_id)
        if connection:
            return connection

        # Try to find by topic message
        connection: QuestionConnection = await self.find_by_topic_message(
            chat_id, message_id
        )
        return connection

    async def get_connections_by_question(
        self, question_token: str
    ) -> list[QuestionConnection]:
        """Get all message connections for a specific question"""
        stmt = select(QuestionConnection).where(
            QuestionConnection.question_token == question_token
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
