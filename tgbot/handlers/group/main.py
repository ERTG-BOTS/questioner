import datetime
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from infrastructure.database.models import User, Dialog
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.topic import IsTopicMessage
from tgbot.keyboards.user.main import user_kb, MainMenu, back_kb, cancel_question_kb
from tgbot.misc.states import Question
from tgbot.services.logger import setup_logging

topic_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@topic_router.message(IsTopicMessage())
async def handle_topic_message(message: Message, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(message.from_user.id)
        topic: Dialog = await repo.dialog_histories.get_dialog_by_topic_id(message.message_thread_id)

    if topic is not None:
        if not topic.TopicDuty:
            await repo.dialog_histories.update_topic_duty(token=topic.Token, topic_duty=duty.FIO)
            employee: User = await repo.users.get_user(fullname=topic.EmployeeFullname)
            await message.bot.send_message(chat_id=employee.ChatId, text=f"""<b>👮‍♂️ Вопрос в работе</b>

Старший <b>{duty.FIO}</b> взял вопрос в работу""")
            await message.bot.copy_message(from_chat_id=config.tg_bot.forum_id, message_id=message.message_id,
                                           chat_id=employee.ChatId)
        else:
            if topic.TopicDuty == duty.FIO:
                await message.bot.copy_message(from_chat_id=config.tg_bot.forum_id, message_id=message.message_id, chat_id=topic.EmployeeChatId)
            else:
                await message.reply("Это не твой чат!")

    else:
        await message.answer(f"""<b>⚠️ Ошибка</b>

Не удалось найти текущий топик в базе, закрываю""")
        await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=message.message_id)
        logger.error(f"Не удалось найти топик {message.message_thread_id}. Закрыли топик")