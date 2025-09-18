from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base


class MessagesPair(Base):
    """Модель для отслеживания связей между сообщениями в вопросах"""

    __tablename__ = "messages_pairs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, nullable=False
    )

    # Инфо о чате с юзером
    user_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Инфо о топике вопроса
    topic_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    topic_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    topic_thread_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Токен вопроса
    question_token: Mapped[str] = mapped_column(String(255), nullable=False)

    # Направление сообщения: 'user_to_topic' или 'topic_to_user'
    direction: Mapped[str] = mapped_column(String(20), nullable=False)

    # Дата сообщения (записи в БД)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<MessagesPair {self.id}>"
