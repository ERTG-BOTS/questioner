from marshmallow.fields import Boolean
from sqlalchemy import BIGINT, BOOLEAN, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base, TableNameMixin


class Employee(Base, TableNameMixin):
    """
    Модель, представляющая сущность пользователя в БД

    Attributes:
        id (Mapped[int]): Уникальный идентификатор пользователя.
        user_id (Mapped[Optional[str]]): Идентификатор чата с пользователем в Telegram.
        username (Mapped[str]): Employeename пользователя в Telegram.
        division (MappedOptional[str]): Направление пользователя (НТП/НЦК).
        position (Mapped[str]): Позиция/должность пользователя.
        fullname (Mapped[str]): ФИО пользователя.
        head (Mapped[str]): ФИО руководителя пользователя.
        email (Mapped[str]): email пользователя.
        role (Mapped[int]): Роль пользователя в БД.

    Methods:
        __repr__(): Returns a string representation of the User object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
    username: Mapped[str] = mapped_column(Unicode, nullable=True)
    division: Mapped[str] = mapped_column(Unicode, nullable=True)
    position: Mapped[str] = mapped_column(Unicode, nullable=True)
    fullname: Mapped[str] = mapped_column(Unicode, nullable=False)
    head: Mapped[str] = mapped_column(Unicode, nullable=True)
    email: Mapped[str] = mapped_column(Unicode, nullable=True)
    role: Mapped[int] = mapped_column(BIGINT, nullable=False)
    is_trainee: Mapped[Boolean] = mapped_column(BOOLEAN, nullable=False)

    def __repr__(self):
        return f"<Employee {self.id} {self.user_id} {self.username} {self.division} {self.position} {self.fullname} {self.head} {self.email} {self.role}>"
