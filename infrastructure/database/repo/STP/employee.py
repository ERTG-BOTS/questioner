import logging
from typing import Optional, Sequence, TypedDict, Unpack

from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models.STP.employee import Employee
from infrastructure.database.repo.base import BaseRepo

logger = logging.getLogger(__name__)


class EmployeeParams(TypedDict, total=False):
    """Доступные параметры для обновления пользователя в таблице RegisteredUsers."""

    user_id: int
    username: str | None
    division: str | None
    position: str | None
    fullname: str
    head: str | None
    email: str | None
    role: int
    is_trainee: bool


class EmployeeRepo(BaseRepo):
    async def get_user(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        fullname: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[Employee]:
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
            filters.append(Employee.user_id == user_id)
        if username:
            filters.append(Employee.username == username)
        if fullname:
            filters.append(Employee.fullname == fullname)
        if email:
            filters.append(Employee.email == email)

        if not filters:
            raise ValueError("At least one parameter must be provided to get_user()")

        # Combine all filters using OR
        query = select(Employee).where(*filters)

        try:
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения пользователя: {e}")
            return None

    async def get_users(
        self, roles: Optional[int | list[int]] = None
    ) -> Sequence[Employee] | None:
        """
        Получить пользователей по роли/ролям

        Args:
            roles: Роль (int) или список ролей (list[int]) для фильтрации.
                  Если None - возвращает всех пользователей

        Returns:
            Список пользователей или None при ошибке
        """
        if roles is not None:
            if isinstance(roles, int):
                # Одна роль
                query = select(Employee).where(Employee.role == roles)
            elif isinstance(roles, list) and roles:
                # Список ролей
                query = select(Employee).where(Employee.role.in_(roles))
            else:
                # Пустой список или некорректный тип
                query = select(Employee)
        else:
            # Все пользователи
            query = select(Employee)

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения списка пользователей: {e}")
            return None

    async def get_unauthorized_users(self, head_name: str = None) -> Sequence[Employee]:
        """
        Получить список неавторизованных пользователей
        Неавторизованные пользователи - те, у которых отсутствует user_id (не связан с Telegram)

        Args:
            head_name: Фильтр по имени руководителя (опционально)

        Returns:
            Список неавторизованных пользователей
        """
        # Основное условие - отсутствие user_id означает что пользователь не авторизован в Telegram
        base_conditions = [Employee.user_id.is_(None)]

        # Добавляем фильтр по руководителю если указан
        if head_name:
            base_conditions.append(Employee.head == head_name)

        query = select(Employee).where(*base_conditions).order_by(Employee.fullname)

        try:
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"[БД] Ошибка получения списка неавторизованных пользователей: {e}"
            )
            return []

    async def update_user(
        self,
        user_id: int = None,
        **kwargs: Unpack[EmployeeParams],
    ) -> Optional[Employee]:
        select_stmt = select(Employee).where(Employee.user_id == user_id)

        result = await self.session.execute(select_stmt)
        user: Employee | None = result.scalar_one_or_none()

        # Если пользователь существует - обновляем его
        if user:
            for key, value in kwargs.items():
                setattr(user, key, value)
            await self.session.commit()

        return user

    async def get_users_by_fio_parts(
        self, fullname: str, limit: int = 10
    ) -> Sequence[Employee]:
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
            like_conditions.append(Employee.fullname.ilike(f"%{part}%"))

        # Все части должны присутствовать в ФИО (AND)
        query = select(Employee).where(and_(*like_conditions)).limit(limit)

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения пользователей по ФИО: {e}")
            return []

    async def get_users_by_head(self, head_name: str) -> Sequence[Employee]:
        """
        Получить всех пользователей с указанным руководителем

        Args:
            head_name: Имя руководителя

        Returns:
            Список пользователей с указанным руководителем
        """
        try:
            result = await self.session.execute(
                select(Employee)
                .where(Employee.head == head_name)
                .order_by(Employee.fullname)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(
                f"Ошибка получения пользователей по руководителю {head_name}: {e}"
            )
            return []

    async def get_admins(self) -> Sequence[Employee]:
        query = select(Employee).where(Employee.role == 10)

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения администраторов: {e}")
            return []

    async def get_users_by_role(
        self, role: int, division: str = None
    ) -> Sequence[Employee]:
        """
        Получить пользователей с определенной ролью

        Args:
            role: Роль пользователя
            division: Направление пользователя. Если указано "НТП", будет искать всех пользователей
                     с division содержащим "НТП" (включая "НТП1", "НТП2" и т.д.)

        Returns:
            Список пользователей с указанной ролью
        """
        if division:
            if division == "НТП":
                query = select(Employee).where(
                    Employee.role == role, Employee.division.ilike(f"%{division}%")
                )
            else:
                query = select(Employee).where(
                    Employee.role == role, Employee.division == division
                )
        else:
            query = select(Employee).where(Employee.role == role)

        try:
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"[БД] Ошибка получения пользователей с ролью {role}: {e}")
            return []

    async def delete_user(self, fullname: str = None, user_id: int = None) -> int:
        """
        Удаление пользователей из БД по полному имени или user_id

        Args:
            fullname: Полное ФИО пользователя для удаления (опционально)
            user_id: ID пользователя для удаления (опционально)

        Returns:
            Количество удаленных пользователей
        """
        if not fullname and not user_id:
            raise ValueError(
                "At least one parameter (fullname or user_id) must be provided"
            )

        try:
            # Строим условие для поиска
            conditions = []
            if fullname:
                conditions.append(Employee.fullname == fullname)
            if user_id:
                conditions.append(Employee.user_id == user_id)

            # Находим пользователей по условиям
            query = select(Employee).where(*conditions)
            result = await self.session.execute(query)
            users = result.scalars().all()

            deleted_count = 0
            for user in users:
                await self.session.delete(user)
                deleted_count += 1
                logger.info(
                    f"[БД] Пользователь {user.fullname} (ID: {user.user_id}) удален из базы данных"
                )

            if deleted_count > 0:
                await self.session.commit()
                identifier = f"ФИО {fullname}" if fullname else f"user_id {user_id}"
                logger.info(
                    f"[БД] Всего удалено {deleted_count} пользователей по {identifier}"
                )

            return deleted_count
        except SQLAlchemyError as e:
            identifier = f"ФИО {fullname}" if fullname else f"user_id {user_id}"
            logger.error(f"[БД] Ошибка удаления пользователей по {identifier}: {e}")
            await self.session.rollback()
            return 0
