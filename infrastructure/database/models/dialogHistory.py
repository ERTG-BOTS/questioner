from typing import Optional

from sqlalchemy import BIGINT, String, Boolean, Integer, Text
from sqlalchemy import Unicode
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TableNameMixin


class DialogHistory(Base, TableNameMixin):
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
        CleverLink (Mapped[Optional[str]]): Ссылка на clever (может быть None).

    Methods:
        __repr__(): Returns a string representation of the DialogHistories object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """
    __tablename__ = 'DialogHistories'

    Token: Mapped[str] = mapped_column(String(255), primary_key=True)
    FIOEmployee: Mapped[str] = mapped_column(Unicode)
    ListFIOSupervisor: Mapped[str] = mapped_column(Unicode)
    StartQuestion: Mapped[str] = mapped_column(Unicode)
    FirstMessageId: Mapped[int] = mapped_column(Integer)
    ListStartDialog: Mapped[str] = mapped_column(Unicode)
    ListEndDialog: Mapped[str] = mapped_column(Unicode)
    DialogQuality: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    MessageThreadId: Mapped[int] = mapped_column(Integer)
    DialogQualityRg: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    CleverLink: Mapped[Optional[str]] = mapped_column(Unicode, nullable=True)

    def __repr__(self):
        return f"<DialogHistories {self.Token} {self.FIOEmployee} {self.FirstMessageId} {self.MessageThreadId}>"