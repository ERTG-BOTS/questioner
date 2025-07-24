from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MessagesPair(Base):
    """Model for tracking message pairs between user chats and forum topics"""

    __tablename__ = "messages_pairs"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, nullable=False
    )

    # Original message info (user chat)
    user_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Copied message info (forum topic)
    topic_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    topic_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    topic_thread_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Question context
    question_token: Mapped[str] = mapped_column(String(255), nullable=False)

    # Direction: 'user_to_topic' or 'topic_to_user'
    direction: Mapped[str] = mapped_column(String(20), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        server_default=func.now(),  # Add server default as well
    )

    def __repr__(self) -> str:
        return (
            f"<QuestionConnection("
            f"id={self.id}, "
            f"user_chat_id={self.user_chat_id}, "
            f"user_message_id={self.user_message_id}, "
            f"topic_message_id={self.topic_message_id}, "
            f"direction='{self.direction}'"
            f")>"
        )
