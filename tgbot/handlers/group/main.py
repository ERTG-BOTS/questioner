import datetime
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from infrastructure.database.models import User, Dialog
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.topic import IsTopicMessage
from tgbot.keyboards.user.main import dialog_quality_kb
from tgbot.misc import dicts
from tgbot.services.logger import setup_logging

topic_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@topic_router.message(IsTopicMessage() and Command("end"))
async def end_cmd(message: Message, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(message.from_user.id)
        topic: Dialog = await repo.dialogs.get_dialog(topic_id=message.message_thread_id)

    if topic is not None:
        if topic.Status != "closed" and topic.TopicDutyFullname == duty.FIO:
            await repo.dialogs.update_dialog_status(token=topic.Token, status="closed")
            await repo.dialogs.update_dialog_end(token=topic.Token, end_time=datetime.datetime.now())

            await message.reply(f"""<b>🔒 Диалог закрыт</b>

Оцени, мог ли специалист решить вопрос самостоятельно""",
                                reply_markup=dialog_quality_kb(token=topic.Token, role="duty"))

            await message.bot.edit_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=topic.TopicId,
                                               icon_custom_emoji_id=dicts.topicEmojis["closed"])
            await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=topic.TopicId)

            employee: User = await repo.users.get_user(fullname=topic.EmployeeFullname)
            await message.bot.send_message(chat_id=employee.ChatId, text=f"""<b>🔒 Диалог закрыт</b>

Старший <b>{duty.FIO}</b> закрыл диалог
Оцени, помогли ли тебе решить вопрос""", reply_markup=dialog_quality_kb(token=topic.Token, role="employee"))
        elif topic.Status != "closed" and topic.TopicDutyFullname != duty.FIO:
            await message.reply("""<b>⚠️ Предупреждение</b>

Это не твой чат!""")
        elif topic.Status == "closed":
            await message.reply("<b>🔒 Диалог был закрыт</b>")
            await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=topic.TopicId)

    else:
        await message.answer(f"""<b>⚠️ Ошибка</b>

Не удалось найти текущий топик в базе, закрываю""")
        await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=message.message_id)
        logger.error(f"Не удалось найти топик {message.message_thread_id}. Закрыли топик")


@topic_router.message(IsTopicMessage() and Command("release"))
async def release_cmd(message: Message, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(message.from_user.id)
        topic: Dialog = await repo.dialogs.get_dialog(topic_id=message.message_thread_id)

    if topic is not None:
        if topic.TopicDutyFullname is not None and topic.TopicDutyFullname == duty.FIO:
            await repo.dialogs.update_topic_duty(token=topic.Token, topic_duty=None)
            await repo.dialogs.update_dialog_status(token=topic.Token, status="open")

            await message.bot.edit_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=topic.TopicId,
                                               icon_custom_emoji_id=dicts.topicEmojis["open"])
            await message.answer(f"""<b>🕊️ Диалог освобожден</b>

Для повторного взятия вопроса в работу напиши сообщение в эту тему""")

            employee: User = await repo.users.get_user(fullname=topic.EmployeeFullname)
            await message.bot.send_message(chat_id=employee.ChatId, text=f"""<b>🕊️ Старший покинул чат</b>

Старший <b>{duty.FIO}</b> закрыл диалог""")
        elif topic.TopicDutyFullname is not None and topic.TopicDutyFullname != duty.FIO:
            await message.reply("""<b>⚠️ Предупреждение</b>

Это не твой чат!""")
        elif topic.TopicDutyFullname is None:
            await message.reply("""<b>⚠️ Предупреждение</b>

Это чат сейчас никем не занят!""")

    else:
        await message.answer(f"""<b>⚠️ Ошибка</b>

Не удалось найти текущий топик в базе, закрываю""")
        await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=message.message_id)
        logger.error(f"Не удалось найти топик {message.message_thread_id}. Закрыли топик")


@topic_router.message(IsTopicMessage())
async def handle_topic_message(message: Message, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(message.from_user.id)
        topic: Dialog = await repo.dialogs.get_dialog(topic_id=message.message_thread_id)

    if topic is not None:
        if not topic.TopicDutyFullname:
            await repo.dialogs.update_topic_duty(token=topic.Token, topic_duty=duty.FIO)
            await repo.dialogs.update_dialog_status(token=topic.Token, status="in_progress")

            duty_topics_today = await repo.dialogs.get_dialogs_count_today(duty_fullname=duty.FIO)
            duty_topics_month = await repo.dialogs.get_dialogs_count_last_month(duty_fullname=duty.FIO)

            await message.bot.edit_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=topic.TopicId,
                                               icon_custom_emoji_id=dicts.topicEmojis["in_progress"])
            await message.answer(f"""<b>👮‍♂️ Вопрос в работе</b>

На вопрос отвечает <b>{duty.FIO}</b> {'(<a href="https://t.me/' + duty.Username + '">лс</a>)' if duty.Username != "Не указан" else ""}

<blockquote expandable><b>⚒️ Решено:</b> за день {duty_topics_today} / за месяц {duty_topics_month}</blockquote>""",
                                 disable_web_page_preview=True)

            employee: User = await repo.users.get_user(fullname=topic.EmployeeFullname)
            await message.bot.send_message(chat_id=employee.ChatId, text=f"""<b>👮‍♂️ Вопрос в работе</b>

Старший <b>{duty.FIO}</b> взял вопрос в работу""")
            await message.bot.copy_message(from_chat_id=config.tg_bot.forum_id, message_id=message.message_id,
                                           chat_id=employee.ChatId)
        else:
            if topic.TopicDutyFullname == duty.FIO:
                await message.bot.copy_message(from_chat_id=config.tg_bot.forum_id, message_id=message.message_id,
                                               chat_id=topic.EmployeeChatId)
            else:
                await message.reply("""<b>⚠️ Предупреждение</b>
                
Это не твой чат!""")

    else:
        await message.answer(f"""<b>⚠️ Ошибка</b>

Не удалось найти текущий топик в базе, закрываю""")
        await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=message.message_id)
        logger.error(f"Не удалось найти топик {message.message_thread_id}. Закрыли топик")
