from aiogram.filters import BaseFilter
from aiogram.types import Message

from infrastructure.database.models.users import Users
from infrastructure.database.repo.requests import RequestsRepo

ADMIN_ROLE = 10


class AdminFilter(BaseFilter):
    is_admin: bool = True

    async def __call__(self, obj: Message, stp_db, **kwargs) -> bool:
        async with stp_db() as session:
            repo = RequestsRepo(session)
            user: Users = await repo.users.get_user(user_id=obj.from_user.id)

            if user is None:
                return False

            return user.Role == ADMIN_ROLE
