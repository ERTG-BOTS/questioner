from typing import Optional

from sqlalchemy import BIGINT, String, Boolean, Integer, Text
from sqlalchemy import Unicode
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TableNameMixin


class DialogHistories(Base, TableNameMixin):
    """
    Класс, представляющий сущность истории диалогов.

    Attributes:
        Token (Mapped[str]): Уникальный идентификатор токена (первичный ключ).
        FIOEmployee (Mapped[str]): ФИО сотрудника.
        ListFIOSupervisor (Mapped[str]): Список ФИО руководителей.
        StartQuestion (Mapped[str]): Начальный вопрос диалога.
        FirstMessageId (Mapped[int]): ID первого сообщения.
        ListStartDialog (Mapped[str]): Список начала диалога.
        ListEndDialog (Mapped[str]): Список окончания диалога.
        DialogQuality (Mapped[Optional[bool]]): Качество диалога от специалиста (может быть None).
        MessageThreadId (Mapped[int]): ID потока сообщений.
        DialogQualityRg (Mapped[Optional[bool]]): Качество диалога от старшего (может быть None).

    Methods:
        __repr__(): Returns a string representation of the DialogHistories object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    Token: Mapped[str] = mapped_column(String(255), primary_key=True)
    FIOEmployee: Mapped[str] = mapped_column(Text)
    ListFIOSupervisor: Mapped[str] = mapped_column(Text)
    StartQuestion: Mapped[str] = mapped_column(Text)
    FirstMessageId: Mapped[int] = mapped_column(Integer)
    ListStartDialog: Mapped[str] = mapped_column(Text)
    ListEndDialog: Mapped[str] = mapped_column(Text)
    DialogQuality: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    MessageThreadId: Mapped[int] = mapped_column(Integer)
    DialogQualityRg: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    def __repr__(self):
        return f"<DialogHistories {self.Token} {self.FIOEmployee} {self.FirstMessageId} {self.MessageThreadId}>"