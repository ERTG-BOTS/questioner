import logging
from typing import Sequence

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Question, User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.topic import IsTopicMessage
from tgbot.handlers.group.cmds import end_q_cmd
from tgbot.keyboards.user.main import (
    QuestionQualityDuty,
    closed_dialog_kb,
    finish_question_kb,
)
from tgbot.misc import dicts
from tgbot.services.logger import setup_logging
from tgbot.services.scheduler import (
    restart_inactivity_timer,
    start_inactivity_timer,
)

topic_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@topic_router.message(IsTopicMessage())
async def handle_q_message(message: Message, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(message.from_user.id)
        topic: Question = await repo.dialogs.get_question(
            topic_id=message.message_thread_id
        )

    if message.text == "✅️ Закрыть вопрос":
        await end_q_cmd(message, stp_db)
        return

    if topic is not None:
        if not topic.TopicDutyFullname:
            await repo.dialogs.update_question_duty(
                token=topic.Token, topic_duty=duty.FIO
            )
            await repo.dialogs.update_question_status(
                token=topic.Token, status="in_progress"
            )

            # Запускаем таймер неактивности для нового вопроса
            if config.tg_bot.activity_status:
                start_inactivity_timer(topic.Token, message.bot, stp_db)

            duty_topics_today = await repo.dialogs.get_questions_count_today(
                duty_fullname=duty.FIO
            )
            duty_topics_month = await repo.dialogs.get_questions_count_last_month(
                duty_fullname=duty.FIO
            )

            await message.bot.edit_forum_topic(
                chat_id=config.tg_bot.forum_id,
                message_thread_id=topic.TopicId,
                icon_custom_emoji_id=dicts.topicEmojis["in_progress"],
            )
            await message.answer(
                f"""<b>👮‍♂️ Вопрос в работе</b>

На вопрос отвечает <b>{duty.FIO}</b> {'(<a href="https://t.me/' + duty.Username + '">лс</a>)' if (duty.Username != "Не указан" or duty.Username != "Скрыто/не определено") else ""}

<blockquote expandable><b>⚒️ Решено:</b> за день {duty_topics_today} / за месяц {duty_topics_month}</blockquote>""",
                disable_web_page_preview=True,
            )

            employee: User = await repo.users.get_user(fullname=topic.EmployeeFullname)
            await message.bot.send_message(
                chat_id=employee.ChatId,
                text=f"""<b>👮‍♂️ Вопрос в работе</b>

Старший <b>{duty.FIO}</b> взял вопрос в работу""",
                reply_markup=finish_question_kb(),
            )
            await message.bot.copy_message(
                from_chat_id=config.tg_bot.forum_id,
                message_id=message.message_id,
                chat_id=employee.ChatId,
            )
        else:
            if topic.TopicDutyFullname == duty.FIO:
                # Перезапускаем таймер неактивности при сообщении от дежурного
                if config.tg_bot.activity_status:
                    restart_inactivity_timer(topic.Token, message.bot, stp_db)

                await message.bot.copy_message(
                    from_chat_id=config.tg_bot.forum_id,
                    message_id=message.message_id,
                    chat_id=topic.EmployeeChatId,
                )
            else:
                await message.reply("""<b>⚠️ Предупреждение</b>
                
Это не твой чат!

<i>Твое сообщение не отобразится специалисту</i>""")

    else:
        await message.answer("""<b>⚠️ Ошибка</b>

Не удалось найти текущую тему в базе, закрываю""")
        await message.bot.close_forum_topic(
            chat_id=config.tg_bot.forum_id, message_thread_id=message.message_id
        )
        logger.error(f"Не удалось найти тему {message.message_thread_id}. Закрыли тему")


@topic_router.callback_query(QuestionQualityDuty.filter(F.return_question))
async def return_q_duty(
    callback: CallbackQuery, callback_data: QuestionQualityDuty, stp_db
):
    await callback.answer()
    async with stp_db() as session:
        repo = RequestsRepo(session)
        employee: User = await repo.users.get_user(user_id=callback.from_user.id)
        question: Question = await repo.dialogs.get_question(token=callback_data.token)
        duty: User = await repo.users.get_user(user_id=callback.from_user.id)
        available_to_return_questions: Sequence[
            Question
        ] = await repo.dialogs.get_available_to_return_questions()

    active_dialogs = await repo.dialogs.get_active_questions()

    if (
        question.Status == "closed"
        and employee.FIO not in [d.EmployeeFullname for d in active_dialogs]
        and question.Token in [d.Token for d in available_to_return_questions]
        and question.TopicDutyFullname == duty.FIO
    ):
        await repo.dialogs.update_question_status(token=question.Token, status="open")
        await callback.bot.edit_forum_topic(
            chat_id=config.tg_bot.forum_id,
            message_thread_id=question.TopicId,
            name=employee.FIO,
            icon_custom_emoji_id=dicts.topicEmojis["open"],
        )
        await callback.bot.reopen_forum_topic(
            chat_id=config.tg_bot.forum_id, message_thread_id=question.TopicId
        )

        await callback.message.answer("""<b>🔓 Вопрос переоткрыт</b>

Можешь писать сообщения, они будут переданы специалисту""")
        await callback.bot.send_message(
            chat_id=question.EmployeeChatId,
            text=f"""<b>🔓 Вопрос переоткрыт</b>

Старший <b>{employee.FIO}</b> переоткрыл вопрос:
<blockquote expandable><i>{question.QuestionText}</i></blockquote>""",
            reply_markup=finish_question_kb(),
        )
    elif question.TopicDutyFullname != duty.FIO:
        await callback.answer("Это не твой чат!", show_alert=True)
    elif employee.FIO in [d.EmployeeFullname for d in active_dialogs]:
        await callback.answer(
            "У специалиста есть другой открытый вопрос", show_alert=True
        )
    elif question.Token not in [d.Token for d in available_to_return_questions]:
        await callback.answer(
            "Вопрос не переоткрыть. Прошло более 24 часов", show_alert=True
        )
    elif question.Status != "closed":
        await callback.answer("Этот вопрос не закрыт", show_alert=True)


@topic_router.callback_query(IsTopicMessage() and QuestionQualityDuty.filter())
async def quality_q_duty(
    callback: CallbackQuery, callback_data: QuestionQualityDuty, stp_db
):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(user_id=callback.from_user.id)
        question: Question = await repo.dialogs.get_question(token=callback_data.token)

    if question.TopicDutyFullname == duty.FIO:
        await repo.dialogs.update_question_quality(
            token=callback_data.token, quality=callback_data.answer, is_duty=True
        )
        await callback.answer("Оценка успешно выставлена ❤️")
        if callback_data.answer:
            await callback.message.edit_text(
                f"""<b>🔒 Вопрос закрыт</b>

<b>{duty.FIO}</b> поставил оценку:
👎 Специалист <b>мог решить вопрос самостоятельно</b>""",
                reply_markup=closed_dialog_kb(token=callback_data.token, role="duty"),
            )
        else:
            await callback.message.edit_text(
                f"""<b>🔒 Вопрос закрыт</b>

<b>{duty.FIO}</b> поставил оценку:
👍 Специалист <b>не мог решить вопрос самостоятельно</b>""",
                reply_markup=closed_dialog_kb(token=callback_data.token, role="duty"),
            )
    else:
        await callback.answer("Это не твой чат!", show_alert=True)
