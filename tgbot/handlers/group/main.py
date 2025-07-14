import datetime
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from infrastructure.database.models import User, Question
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.topic import IsTopicMessage, IsTopicMessageWithCommand
from tgbot.keyboards.user.main import dialog_quality_kb, QuestionQualityDuty, closed_dialog_kb
from tgbot.misc import dicts
from tgbot.services.logger import setup_logging

topic_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@topic_router.message(IsTopicMessageWithCommand("end"))
async def end_cmd(message: Message, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(message.from_user.id)
        topic: Question = await repo.dialogs.get_dialog(topic_id=message.message_thread_id)

    if topic is not None:
        if topic.Status != "closed" and topic.TopicDutyFullname == duty.FIO:
            await repo.dialogs.update_dialog_status(token=topic.Token, status="closed")
            await repo.dialogs.update_dialog_end(token=topic.Token, end_time=datetime.datetime.now())

            await message.reply(f"""<b>🔒 Вопрос закрыт</b>

Оцени, мог ли специалист решить его самостоятельно""",
                                reply_markup=dialog_quality_kb(token=topic.Token, role="duty"))

            await message.bot.edit_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=topic.TopicId,
                                               name=topic.Token,
                                               icon_custom_emoji_id=dicts.topicEmojis["closed"])
            await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=topic.TopicId)

            employee: User = await repo.users.get_user(fullname=topic.EmployeeFullname)
            await message.bot.send_message(chat_id=employee.ChatId, text=f"""<b>🔒 Вопрос закрыт</b>

Старший <b>{duty.FIO}</b> закрыл вопрос
Оцени, помогли ли тебе решить его""", reply_markup=dialog_quality_kb(token=topic.Token, role="employee"))
        elif topic.Status != "closed" and topic.TopicDutyFullname != duty.FIO:
            await message.reply("""<b>⚠️ Предупреждение</b>

Это не твой чат!""")
        elif topic.Status == "closed":
            await message.reply("<b>🔒 Вопрос был закрыт</b>")
            await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=topic.TopicId)

    else:
        await message.answer(f"""<b>⚠️ Ошибка</b>

Не удалось найти текущую тему в базе""")
        logger.error(f"Не удалось найти тему {message.message_thread_id}")


@topic_router.message(IsTopicMessageWithCommand("release"))
async def release_cmd(message: Message, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(message.from_user.id)
        topic: Question = await repo.dialogs.get_dialog(topic_id=message.message_thread_id)

    if topic is not None:
        if topic.TopicDutyFullname is not None and topic.TopicDutyFullname == duty.FIO:
            await repo.dialogs.update_topic_duty(token=topic.Token, topic_duty=None)
            await repo.dialogs.update_dialog_status(token=topic.Token, status="open")

            await message.bot.edit_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=topic.TopicId,
                                               icon_custom_emoji_id=dicts.topicEmojis["open"])
            await message.answer(f"""<b>🕊️ Вопрос освобожден</b>

Для повторного взятия вопроса в работу напиши сообщение в эту тему""")

            employee: User = await repo.users.get_user(fullname=topic.EmployeeFullname)
            await message.bot.send_message(chat_id=employee.ChatId, text=f"""<b>🕊️ Старший покинул чат</b>

Старший <b>{duty.FIO}</b> освободил вопрос. Ожидай повторного подключения старшего""")
        elif topic.TopicDutyFullname is not None and topic.TopicDutyFullname != duty.FIO:
            await message.reply("""<b>⚠️ Предупреждение</b>

Это не твой чат!""")
        elif topic.TopicDutyFullname is None:
            await message.reply("""<b>⚠️ Предупреждение</b>

Это чат сейчас никем не занят!""")

    else:
        await message.answer(f"""<b>⚠️ Ошибка</b>

Не удалось найти текущую тему в базе, закрываю""")
        await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=message.message_id)
        logger.error(f"Не удалось найти тему {message.message_thread_id}. Закрыли тему")


@topic_router.message(IsTopicMessage())
async def handle_topic_message(message: Message, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(message.from_user.id)
        topic: Question = await repo.dialogs.get_dialog(topic_id=message.message_thread_id)

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

Не удалось найти текущую тему в базе, закрываю""")
        await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=message.message_id)
        logger.error(f"Не удалось найти тему {message.message_thread_id}. Закрыли тему")


@topic_router.callback_query(QuestionQualityDuty.filter(F.return_dialog == True))
async def return_dialog_by_duty(callback: CallbackQuery, callback_data: QuestionQualityDuty, stp_db):
    await callback.answer()
    async with stp_db() as session:
        repo = RequestsRepo(session)
        employee: User = await repo.users.get_user(user_id=callback.from_user.id)
        dialog: Question = await repo.dialogs.get_dialog(token=callback_data.token)
        duty: User = await repo.users.get_user(user_id=callback.from_user.id)

    active_dialogs = await repo.dialogs.get_active_dialogs()

    if dialog.Status == "closed" and employee.FIO not in [d.EmployeeFullname for d in active_dialogs] and dialog.TopicDutyFullname == duty.FIO:
        await repo.dialogs.update_dialog_status(token=dialog.Token, status="open")
        await callback.bot.edit_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId,
                                            name=employee.FIO, icon_custom_emoji_id=dicts.topicEmojis["open"])
        await callback.bot.reopen_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId)

        await callback.message.answer(f"""<b>🔓 Вопрос переоткрыт</b>

Можешь писать сообщения, они будут переданы специалисту""")
        await callback.bot.send_message(chat_id=dialog.EmployeeChatId, text=f"""<b>🔓 Вопрос переоткрыт</b>

Старший <b>{employee.FIO}</b> переоткрыл вопрос:
<blockquote expandable><i>{dialog.QuestionText}</i></blockquote>""")
    elif dialog.TopicDutyFullname != duty.FIO:
        await callback.answer("Это не твой чат!", show_alert=True)
    elif employee.FIO in [d.EmployeeFullname for d in active_dialogs]:
        await callback.answer("У специалиста есть другой открытый вопрос", show_alert=True)
    elif dialog.Status != "closed":
        await callback.answer("Этот вопрос не закрыт", show_alert=True)


@topic_router.callback_query(IsTopicMessage() and QuestionQualityDuty.filter())
async def dialog_quality_duty(callback: CallbackQuery, callback_data: QuestionQualityDuty, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(user_id=callback.from_user.id)
        dialog: Question = await repo.dialogs.get_dialog(token=callback_data.token)

    if dialog.TopicDutyFullname == duty.FIO:
        await repo.dialogs.update_dialog_quality(token=callback_data.token, quality=callback_data.answer, is_duty=True)
        await callback.answer("Оценка успешно выставлена ❤️")
        if callback_data.answer:
            await callback.message.edit_text(f"""<b>🔒 Вопрос закрыт</b>

<b>{duty.FIO}</b> поставил оценку:
👎 Специалист <b>мог решить вопрос самостоятельно</b>""",
                                             reply_markup=closed_dialog_kb(token=callback_data.token, role="duty"))
        else:
            await callback.message.edit_text(f"""<b>🔒 Вопрос закрыт</b>

<b>{duty.FIO}</b> поставил оценку:
👍 Специалист <b>не мог решить вопрос самостоятельно</b>""",
                                             reply_markup=closed_dialog_kb(token=callback_data.token, role="duty"))
    else:
        await callback.answer("Это не твой чат!", show_alert=True)
