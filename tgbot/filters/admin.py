from aiogram.filters import BaseFilter
from aiogram.types import Message

from infrastructure.database.models.user import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.misc.dicts import executed_codes

ADMIN_ROLE = 10


class AdminFilter(BaseFilter):
    async def __call__(self, obj: Message, repo: RequestsRepo, **kwargs) -> bool:
        user: User = await repo.users.get_user(user_id=obj.from_user.id)

        if user is None:
            return False

        return user.Role == executed_codes["root"]
