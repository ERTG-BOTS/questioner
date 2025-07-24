from typing import Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import MessagesPair


class MessagesPairsRepo:
    """Repository for managing message connections between user chats and forum topics"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_pair(
        self,
        user_chat_id: int,
        user_message_id: int,
        topic_chat_id: int,
        topic_message_id: int,
        topic_thread_id: Optional[int],
        question_token: str,
        direction: str,
    ) -> MessagesPair:
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
            Created MessagesPair instance
        """
        connection = MessagesPair(
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
    ) -> Optional[MessagesPair]:
        """Find connection by user chat message"""
        stmt = select(MessagesPair).where(
            and_(
                MessagesPair.user_chat_id == user_chat_id,
                MessagesPair.user_message_id == user_message_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_topic_message(
        self, topic_chat_id: int, topic_message_id: int
    ) -> Optional[MessagesPair]:
        """Find connection by topic message"""
        stmt = select(MessagesPair).where(
            and_(
                MessagesPair.topic_chat_id == topic_chat_id,
                MessagesPair.topic_message_id == topic_message_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_pair_for_edit(
        self, chat_id: int, message_id: int
    ) -> Optional[MessagesPair]:
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
        connection: MessagesPair = await self.find_by_topic_message(chat_id, message_id)
        return connection

    async def get_pairs_by_question(self, question_token: str) -> list[MessagesPair]:
        """Get all message connections for a specific question"""
        stmt = select(MessagesPair).where(MessagesPair.question_token == question_token)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_old_pairs(self) -> Sequence[MessagesPair]:
        """
        Получает пары сообщений старше 2 дней.

        Returns:
            Sequence[MessagesPair]: Список пар сообщений старше 2 ней
        """
        from datetime import datetime, timedelta

        # Считаем дату два дня назад
        today = datetime.now()
        two_days_ago = today - timedelta(days=2)

        stmt = select(MessagesPair).where(MessagesPair.created_at < two_days_ago)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_pairs(self, pairs: Sequence[MessagesPair] = None) -> dict:
        """
        Удаляет старые пары сообщений из базы данных.

        Args:
            pairs (Sequence[QuestionConnection], optional): Последовательность связей для удаления.
                                                                Если не указано, получает их автоматически.

        Returns:
            dict: Результат операции с ключами:
                - success (bool): True если операция выполнена успешно
                - deleted_count (int): Количество удаленных связей
                - total_count (int): Общее количество связей для удаления
                - errors (list): Список ошибок, если они возникли
        """
        deleted_count = 0
        errors = []

        try:
            total_count = len(pairs)

            if total_count == 0:
                return {
                    "success": True,
                    "deleted_count": 0,
                    "total_count": 0,
                    "errors": [],
                }

            # Удаляем каждую связь
            for connection in pairs:
                try:
                    # Обновляем объект в текущей сессии
                    await self.session.refresh(connection)
                    await self.session.delete(connection)
                    deleted_count += 1
                except Exception as e:
                    errors.append(
                        f"Error deleting connection {connection.id}: {str(e)}"
                    )

            await self.session.commit()

            return {
                "success": deleted_count > 0,
                "deleted_count": deleted_count,
                "total_count": total_count,
                "errors": errors,
            }

        except Exception as e:
            # Откатываем изменения в случае ошибки
            await self.session.rollback()
            errors.append(f"Database error: {str(e)}")

            return {
                "success": False,
                "deleted_count": deleted_count,
                "total_count": total_count if "total_count" in locals() else 0,
                "errors": errors,
            }
