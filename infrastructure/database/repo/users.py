import logging
from typing import Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.user import User
from infrastructure.database.repo.base import BaseRepo
from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class UserRepo(BaseRepo):
    async def get_user(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        fullname: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[User]:
        """
        Поиск пользователя в БД по фильтрам

        Args:
            user_id: Уникальный идентификатор пользователя Telegram
            username: Никнейм пользователя Telegram
            fullname: ФИО пользователя в БД
            email: Почта пользователя в БД

        Returns:
            Объект User или ничего
        """
        filters = []

        if user_id:
            filters.append(User.ChatId == user_id)
        if username:
            filters.append(User.Username == username)
        if fullname:
            filters.append(User.FIO == fullname)
        if email:
            filters.append(User.Email == email)

        if not filters:
            raise ValueError("At least one parameter must be provided to get_user()")

        # Combine all filters using OR
        query = select(User).where(*filters)

        try:
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения пользователя: {e}")
            return None

    async def get_users_by_fio_parts(
        self, fullname: str, limit: int = 10
    ) -> Sequence[User]:
        """
        Поиск пользователей по частичному совпадению ФИО
        Возвращает список пользователей для случаев, когда найдено несколько совпадений

        Args:
            fullname: Частичное или полное ФИО для поиска
            limit: Максимальное количество результатов

        Returns:
            Список объектов User
        """
        name_parts = fullname.strip().split()
        if not name_parts:
            return []

        # Создаём условия для каждой части имени
        like_conditions = []
        for part in name_parts:
            like_conditions.append(User.FIO.ilike(f"%{part}%"))

        # Все части должны присутствовать в ФИО (AND)
        query = select(User).where(and_(*like_conditions)).limit(limit)

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения пользователей по ФИО: {e}")
            return []

    async def get_admins(self) -> Sequence[User]:
        query = select(User).where(User.Role == 10)

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения администраторов: {e}")
            return []
