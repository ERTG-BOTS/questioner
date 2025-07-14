import asyncio
import datetime
import logging

import pytz
from aiogram import Bot
from aiogram.utils.i18n import I18n
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import infrastructure.database.repo.requests as db
from tgbot.config import load_config
from tgbot.services.logger import setup_logging

scheduler = AsyncIOScheduler(timezone=pytz.utc)
config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


async def delete_messages(bot: Bot, chat_id: int, message_ids: list[int]):
    """Удаляет список сообщений."""
    try:
        for message_id in message_ids:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Ошибка при удалении сообщений: {e}")


async def run_delete_timer(bot: Bot, chat_id: int, message_ids: list[int], seconds: int = 60):
    """Delete messages after timer. Default - 60 seconds."""
    try:
        scheduler.add_job(delete_messages, "date",
                          run_date=datetime.datetime.now(tz=pytz.utc) + datetime.timedelta(seconds=seconds),
                          args=[bot, chat_id, message_ids], )
    except Exception as e:
        print(f"Ошибка при планировании удаления сообщений: {e}")


async def remove_old_topics(bot: Bot):
    pass