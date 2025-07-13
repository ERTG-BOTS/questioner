import datetime
from typing import Optional
from datetime import date

from sqlalchemy import BIGINT, String, Boolean, Integer, Date, DateTime
from sqlalchemy import Unicode
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TableNameMixin


class Dialog(Base, TableNameMixin):
    """
    Класс, представляющий сущность диалогов.

    Attributes:
        Token (Mapped[str]): Уникальный идентификатор токена (первичный ключ).
        TopicId (Mapped[int]): ID топика.
        TopicDuty (Mapped[str]): ФИО ответственного за вопрос.
        EmployeeFullname (Mapped[str]): ФИО сотрудника.
        EmployeeChatId (Mapped[int]): Chat ID сотрудника.
        Question (Mapped[str]): Вопрос диалога.
        StartTime (Mapped[Optional[date]]): Время начала диалога.
        EndTime (Mapped[Optional[date]]): Время окончания диалога.
        CleverLink (Mapped[Optional[str]]): Ссылка на clever (может быть None).
        DialogQualityEmployee (Mapped[Optional[bool]]): Качество диалога от сотрудника (может быть None).
        DialogQualityDuty (Mapped[Optional[bool]]): Качество диалога от дежурного (может быть None).

    Methods:
        __repr__(): Returns a string representation of the Dialog object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.
    """
    __tablename__ = 'DialogsNew'

    Token: Mapped[str] = mapped_column(String(255), primary_key=True)
    TopicId: Mapped[int] = mapped_column(Integer, nullable=False)
    TopicDuty: Mapped[str] = mapped_column(Unicode)
    EmployeeFullname: Mapped[str] = mapped_column(Unicode, nullable=False)
    EmployeeChatId: Mapped[int] = mapped_column(BIGINT, nullable=False)
    Question: Mapped[str] = mapped_column(Unicode, nullable=False)
    StartTime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    EndTime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    CleverLink: Mapped[Optional[str]] = mapped_column(Unicode, nullable=True)
    DialogQualityEmployee: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    DialogQualityDuty: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    def __repr__(self):
        return f"<Dialog {self.Token} {self.TopicId} {self.TopicDuty} {self.EmployeeFullname} {self.EmployeeChatId} {self.Question} {self.StartTime} {self.EndTime} {self.CleverLink} {self.DialogQualityEmployee} {self.DialogQualityDuty}>"