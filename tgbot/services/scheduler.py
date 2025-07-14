import asyncio
import datetime
import logging

import pytz
from aiogram import Bot
from aiogram.utils.i18n import I18n
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import Sequence

from infrastructure.database.models import Question
from infrastructure.database.repo.requests import RequestsRepo
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


async def remove_old_topics(bot: Bot, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        old_questions: Sequence[Question] = await repo.dialogs.get_old_questions()

        for question in old_questions:
            await bot.delete_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=question.TopicId)

        result = await repo.dialogs.delete_question(dialogs=old_questions)
        logger.info(f"[Старые топики] Успешно удалено {result['deleted_count']} из {result['total_count']} старых вопросов")
        if result['errors']:
            logger.info(f"[Старые топики] Произошла ошибка при удалении части вопросов: {result['errors']}")