import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Unicode, BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class Question(Base, TableNameMixin):
    """
    Модель, представляющая сущность вопроса в БД

    Attributes:
        token (Mapped[str]): Уникальный идентификатор токена (первичный ключ).
        group_id (Mapped[int]): ID группы.
        topic_id (Mapped[int]): ID топика.
        duty_userid (Mapped[str]): userid дежурного.
        employee_userid (Mapped[int]): Chat ID сотрудника.
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
    group_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    topic_id: Mapped[int] = mapped_column(Integer, nullable=False)
    duty_userid: Mapped[int] = mapped_column(BIGINT, nullable=True)
    employee_userid: Mapped[int] = mapped_column(BIGINT, nullable=False)
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
        return f"<Question {self.token}>"
