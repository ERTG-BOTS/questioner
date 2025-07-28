import datetime
from typing import Optional

from sqlalchemy import BIGINT, Boolean, DateTime, Integer, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TableNameMixin


class Question(Base, TableNameMixin):
    """
    Модель, представляющая сущность вопроса в БД

    Attributes:
        token (Mapped[str]): Уникальный идентификатор токена (первичный ключ).
        group_id (Mapped[int]): ID группы.
        topic_id (Mapped[int]): ID топика.
        topic_duty_fullname (Mapped[str]): ФИО ответственного за вопрос.
        employee_fullname (Mapped[str]): ФИО сотрудника.
        employee_chat_id (Mapped[int]): Chat ID сотрудника.
        employee_division (Mapped[int]): Направление сотрудника.
        question_text (Mapped[str]): Текст вопроса.
        start_time (Mapped[Optional[date]]): Время начала вопроса.
        end_time (Mapped[Optional[date]]): Время окончания вопроса.
        clever_link (Mapped[Optional[str]]): Ссылка на clever (может быть None).
        quality_employee (Mapped[Optional[bool]]): Качество вопроса от сотрудника (может быть None).
        quality_duty (Mapped[Optional[bool]]): Качество вопроса от дежурного (может быть None).
        status (Mapped[Optional[str]]): Статус вопроса.
        allow_return ([Mapped[Optional[bool]]): Статус доступности вопроса к возврату
        activity_status_enabled (Mapped[Optional[bool]]): Персональная настройка статуса активности для топика (может быть None)

    Methods:
        __repr__(): Returns a string representation of the Question object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.
    """

    __tablename__ = "questions"

    token: Mapped[str] = mapped_column(String(255), primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_id: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_duty_fullname: Mapped[Optional[str]] = mapped_column(Unicode, nullable=True)
    employee_fullname: Mapped[str] = mapped_column(Unicode, nullable=False)
    employee_chat_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    employee_division: Mapped[str] = mapped_column(Unicode, nullable=False)
    question_text: Mapped[str] = mapped_column(Unicode, nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    clever_link: Mapped[Optional[str]] = mapped_column(Unicode, nullable=True)
    quality_employee: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    quality_duty: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Unicode, nullable=True)
    allow_return: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    activity_status_enabled: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, default=None
    )

    def __repr__(self):
        return f"<Question {self.token} {self.group_id} {self.topic_id} {self.topic_duty_fullname} {self.employee_fullname} {self.employee_chat_id} {self.employee_division} {self.question_text} {self.start_time} {self.end_time} {self.clever_link} {self.quality_employee} {self.quality_duty} {self.status} {self.allow_return} {self.activity_status_enabled}>"
