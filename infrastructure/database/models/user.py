from sqlalchemy import BIGINT, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TableNameMixin


class User(Base, TableNameMixin):
    """
    Модель, представляющая сущность пользователя в БД

    Attributes:
        id (Mapped[int]): Уникальный идентификатор пользователя.
        ChatId (Mapped[Optional[str]]): Идентификатор чата с пользователем в Telegram.
        Username (Mapped[str]): Username пользователя в Telegram.
        Division (MappedOptional[str]): Направление пользователя (НТП/НЦК).
        Position (Mapped[str]): Позиция/должность пользователя.
        FIO (Mapped[str]): ФИО пользователя.
        Boss (Mapped[str]): ФИО руководителя пользователя.
        Email (Mapped[str]): Email пользователя.
        Role (Mapped[int]): Роль пользователя в БД.

    Methods:
        __repr__(): Returns a string representation of the User object.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.

    """

    __tablename__ = "RegisteredUsers"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    ChatId: Mapped[int] = mapped_column(BIGINT)
    Username: Mapped[str] = mapped_column(Unicode)
    Division: Mapped[str] = mapped_column(Unicode)
    Position: Mapped[str] = mapped_column(Unicode)
    FIO: Mapped[str] = mapped_column(Unicode)
    Boss: Mapped[str] = mapped_column(Unicode)
    Email: Mapped[str] = mapped_column(Unicode)
    Role: Mapped[int] = mapped_column(BIGINT)

    def __repr__(self):
        return f"<User {self.id} {self.ChatId} {self.Username} {self.Division} {self.Position} {self.FIO} {self.Boss} {self.Email} {self.Role}>"
