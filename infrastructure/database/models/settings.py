import json
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import BIGINT, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TableNameMixin


class Settings(Base, TableNameMixin):
    """
    Модель, представляющая настройки группы в БД

    Attributes:
        id (Mapped[int]): Уникальный идентификатор настроек (первичный ключ).
        group_id (Mapped[int]): ID группы Telegram (уникальный).
        values (Mapped[str]): JSON строка с настройками группы.
        last_update (Mapped[datetime]): Дата последнего обновления настроек.

    Methods:
        __repr__(): Returns a string representation of the Settings object.
        get_values(): Returns parsed JSON values as dictionary.
        set_values(values_dict): Sets values from dictionary, converting to JSON.
        get_setting(key, default): Gets specific setting value with default.
        set_setting(key, value): Sets specific setting value.

    Inherited Attributes:
        Inherits from Base and TableNameMixin classes, which provide additional attributes and functionality.

    Inherited Methods:
        Inherits methods from Base and TableNameMixin classes, which provide additional functionality.
    """

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(
        BIGINT, primary_key=True, autoincrement=True, nullable=False
    )
    group_id: Mapped[int] = mapped_column(BIGINT, nullable=False, unique=True)
    values: Mapped[str] = mapped_column(
        String, nullable=False, default='"{}"', server_default='"{}"'
    )
    last_update: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Settings id={self.id} group_id={self.group_id} last_update={self.last_update}>"

    def get_values(self) -> Dict[str, Any]:
        """
        Получение настроек в виде словаря
        :return: Словарь с настройками
        """
        try:
            return json.loads(self.values)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_values(self, values_dict: Dict[str, Any]) -> None:
        """
        Установка настроек из словаря
        :param values_dict: Словарь с настройками
        """
        self.values = json.dumps(values_dict, ensure_ascii=False)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Получение конкретной настройки
        :param key: Ключ настройки
        :param default: Значение по умолчанию
        :return: Значение настройки или default
        """
        values = self.get_values()
        return values.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """
        Установка конкретной настройки
        :param key: Ключ настройки
        :param value: Значение настройки
        """
        values = self.get_values()
        values[key] = value
        self.set_values(values)
