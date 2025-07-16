import datetime
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from infrastructure.database.models import Question, User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.topic import IsTopicMessageWithCommand
from tgbot.keyboards.user.main import (
    FinishedQuestion,
    dialog_quality_kb,
)
from tgbot.misc import dicts
from tgbot.services.logger import setup_logging
from tgbot.services.scheduler import (
    stop_inactivity_timer,
)

topic_cmds_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@topic_cmds_router.message(IsTopicMessageWithCommand("end"))
async def end_q_cmd(message: Message, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(message.from_user.id)
        question: Question = await repo.dialogs.get_question(
            topic_id=message.message_thread_id
        )

    if question is not None:
        if question.Status != "closed" and question.TopicDutyFullname == duty.FIO:
            # Останавливаем таймер неактивности
            stop_inactivity_timer(question.Token)

            await repo.dialogs.update_question_status(
                token=question.Token, status="closed"
            )
            await repo.dialogs.update_question_end(
                token=question.Token, end_time=datetime.datetime.now()
            )

            await message.reply(
                """<b>🔒 Вопрос закрыт</b>

Оцени, мог ли специалист решить его самостоятельно""",
                reply_markup=dialog_quality_kb(token=question.Token, role="duty"),
            )

            await message.bot.edit_forum_topic(
                chat_id=config.tg_bot.forum_id,
                message_thread_id=question.TopicId,
                name=question.Token,
                icon_custom_emoji_id=dicts.topicEmojis["closed"],
            )
            await message.bot.close_forum_topic(
                chat_id=config.tg_bot.forum_id, message_thread_id=question.TopicId
            )

            employee: User = await repo.users.get_user(fullname=question.EmployeeFullname)

            await message.bot.send_message(
                chat_id=employee.ChatId,
                text="<b>🔒 Вопрос закрыт</b>",
                reply_markup=ReplyKeyboardRemove(),
            )

            await message.bot.send_message(
                chat_id=employee.ChatId,
                text=f"""Старший <b>{duty.FIO}</b> закрыл вопрос
Оцени, помогли ли тебе решить его""",
                reply_markup=dialog_quality_kb(token=question.Token, role="employee"),
            )
        elif question.Status != "closed" and question.TopicDutyFullname != duty.FIO:
            await message.reply("""<b>⚠️ Предупреждение</b>

Это не твой чат!

<i>Твое сообщение не отобразится специалисту</i>""")
        elif question.Status == "closed":
            await message.reply("<b>🔒 Вопрос был закрыт</b>")
            await message.bot.close_forum_topic(
                chat_id=config.tg_bot.forum_id, message_thread_id=question.TopicId
            )

    else:
        await message.answer("""<b>⚠️ Ошибка</b>

Не удалось найти текущую тему в базе""")
        logger.error(f"Не удалось найти тему {message.message_thread_id}")


@topic_cmds_router.message(IsTopicMessageWithCommand("release"))
async def release_q_cmd(message: Message, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(message.from_user.id)
        topic: Question = await repo.dialogs.get_question(
            topic_id=message.message_thread_id
        )

    if topic is not None:
        if topic.TopicDutyFullname is not None and topic.TopicDutyFullname == duty.FIO:
            await repo.dialogs.update_question_duty(token=topic.Token, topic_duty=None)
            await repo.dialogs.update_question_status(token=topic.Token, status="open")

            await message.bot.edit_forum_topic(
                chat_id=config.tg_bot.forum_id,
                message_thread_id=topic.TopicId,
                icon_custom_emoji_id=dicts.topicEmojis["open"],
            )
            await message.answer("""<b>🕊️ Вопрос освобожден</b>

Для взятия вопроса в работу напишите сообщение в эту тему""")

            employee: User = await repo.users.get_user(fullname=topic.EmployeeFullname)
            await message.bot.send_message(
                chat_id=employee.ChatId,
                text=f"""<b>🕊️ Старший покинул чат</b>

Старший <b>{duty.FIO}</b> освободил вопрос. Ожидай повторного подключения старшего""",
            )
        elif (
            topic.TopicDutyFullname is not None and topic.TopicDutyFullname != duty.FIO
        ):
            await message.reply("""<b>⚠️ Предупреждение</b>

Это не твой чат!

<i>Твое сообщение не отобразится специалисту</i>""")
        elif topic.TopicDutyFullname is None:
            await message.reply("""<b>⚠️ Предупреждение</b>

Это чат сейчас никем не занят!""")

    else:
        await message.answer("""<b>⚠️ Ошибка</b>

Не удалось найти текущую тему в базе, закрываю""")
        await message.bot.close_forum_topic(
            chat_id=config.tg_bot.forum_id, message_thread_id=message.message_id
        )
        logger.error(f"Не удалось найти тему {message.message_thread_id}. Закрыли тему")


@topic_cmds_router.callback_query(FinishedQuestion.filter(F.action == "release"))
async def release_q_cb(callback: CallbackQuery, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        topic: Question = await repo.dialogs.get_question(
            topic_id=callback.message.message_thread_id
        )

    if topic is not None:
        await repo.dialogs.update_question_duty(token=topic.Token, topic_duty=None)
        await repo.dialogs.update_question_status(token=topic.Token, status="open")

        await callback.message.answer("""<b>🕊️ Вопрос освобожден</b>

Для взятия вопроса в работу напишите сообщение в эту тему""")

    else:
        await callback.message.answer("""<b>⚠️ Ошибка</b>

Не удалось найти текущую тему в базе, закрываю""")
        await callback.bot.close_forum_topic(
            chat_id=config.tg_bot.forum_id,
            message_thread_id=callback.message.message_id,
        )
        logger.error(
            f"Не удалось найти тему {callback.message_thread_id}. Закрыли тему"
        )