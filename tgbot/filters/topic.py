from aiogram.filters import BaseFilter
from aiogram.types import Message


class IsTopicMessage(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.message_thread_id is not None and message.from_user.id != message.bot.id