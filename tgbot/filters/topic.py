import logging

from aiogram.filters import BaseFilter
from aiogram.types import Message


from aiogram.filters import BaseFilter
from aiogram.types import Message

from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class IsTopicMessage(BaseFilter):
    """Passes only for user messages that belong to a forum‑topic thread."""

    async def __call__(self, message: Message, **_) -> bool:
        # Check if it's actually in a forum/supergroup
        if message.chat.type not in ['supergroup', 'group']:
            return False

        # Check if it's in a topic thread
        in_topic = bool(message.is_topic_message and message.message_thread_id)
        if not in_topic:
            return False

        # Ignore service messages or posts sent on behalf of a channel
        if message.from_user is None:
            return False

        # Ignore the bot's own messages
        if message.from_user.id == message.bot.id:
            return False

        return True


class IsTopicMessageWithCommand(BaseFilter):
    def __init__(self, command: str = None):
        self.command = command

    async def __call__(self, message: Message, **_) -> bool:
        if self.command:
            if not message.text or not message.text.startswith(f"/{self.command}"):
                return False

        # Check if it's actually in a forum/supergroup
        if message.chat.type not in ['supergroup', 'group']:
            return False

        # Check if it's in a topic thread
        in_topic = bool(message.is_topic_message and message.message_thread_id)
        if not in_topic:
            return False

        # Ignore service messages or posts sent on behalf of a channel
        if message.from_user is None:
            return False

        # Ignore the bot's own messages
        if message.from_user.id == message.bot.id:
            return False

        return True