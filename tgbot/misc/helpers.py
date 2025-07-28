import logging
import re

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def disable_previous_buttons(message: Message, state: FSMContext):
    """Функция для отключения inline кнопок в сообщениях"""
    state_data = await state.get_data()
    messages_with_buttons = state_data.get("messages_with_buttons", [])

    for msg_id in messages_with_buttons:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id, message_id=msg_id, reply_markup=None
            )
        except Exception as e:
            # Handle case where message might be deleted or not editable
            print(f"Could not disable buttons for message {msg_id}: {e}")

    # Clear the list after disabling buttons
    await state.update_data(messages_with_buttons=[])


async def check_premium_emoji(message: Message) -> tuple[bool, list[str]]:
    emoji_ids = []
    if message.entities:
        for entity in message.entities:
            if entity.type == "custom_emoji":
                emoji_ids.append(entity.custom_emoji_id)
    return len(emoji_ids) > 0, emoji_ids


def extract_clever_link(message_text):
    pattern = r"https?://[^\s]*clever\.ertelecom\.ru/content/space/[^\s]*"

    match = re.search(pattern, message_text)
    if match:
        return match.group(0)
    return None
