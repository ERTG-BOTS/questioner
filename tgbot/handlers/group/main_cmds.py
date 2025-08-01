import logging

from aiogram import Router
from aiogram.types import Message

from tgbot.config import load_config
from tgbot.filters.topic import IsMainTopicMessageWithCommand
from tgbot.services.logger import setup_logging

main_topic_cmds_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@main_topic_cmds_router.message(IsMainTopicMessageWithCommand("link"))
async def link_cmd(message: Message):
    group_link = await message.bot.export_chat_invite_link(chat_id=message.chat.id)
    await message.answer(
        f"Пригласительная ссылка на этот чат:\n<code>{group_link}</code>"
    )
