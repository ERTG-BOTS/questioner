import datetime
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

from infrastructure.database.models import User, Question
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.active_question import ActiveQuestion, ActiveQuestionWithCommand
from tgbot.keyboards.user.main import QuestionQualitySpecialist, dialog_quality_kb, closed_dialog_kb, finish_question_kb
from tgbot.misc import dicts
from tgbot.services.logger import setup_logging
from tgbot.services.scheduler import stop_inactivity_timer, restart_inactivity_timer

user_dialog_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@user_dialog_router.message(ActiveQuestionWithCommand("end"))
async def active_question_end(message: Message, stp_db, active_dialog_token: str = None):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        employee: User = await repo.users.get_user(message.from_user.id)
        dialog: Question = await repo.dialogs.get_question(token=active_dialog_token)

    if dialog is not None:
        if dialog.Status != "closed":
            # Останавливаем таймер неактивности
            stop_inactivity_timer(dialog.Token)

            await repo.dialogs.update_question_status(token=dialog.Token, status="closed")
            await repo.dialogs.update_question_end(token=dialog.Token, end_time=datetime.datetime.now())

            await message.bot.send_message(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId, text=f"""<b>🔒 Вопрос закрыт</b>

Специалист <b>{employee.FIO}</b> закрыл вопрос
Оцени, мог ли специалист решить вопрос самостоятельно""",
                                           reply_markup=dialog_quality_kb(token=dialog.Token, role="duty"))

            await message.bot.edit_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId,
                                               name=dialog.Token,
                                               icon_custom_emoji_id=dicts.topicEmojis["closed"])
            await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId)

            await message.reply(text="<b>🔒 Вопрос закрыт</b>",
                                           reply_markup=ReplyKeyboardRemove())
            await message.answer(f"""Ты закрыл вопрос
Оцени, помогли ли тебе решить вопрос""", reply_markup=dialog_quality_kb(token=dialog.Token, role="employee"))
        elif dialog.Status == "closed":
            await message.reply("<b>🔒 Вопрос был закрыт</b>")
            await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId)

    else:
        await message.answer(f"""<b>⚠️ Ошибка</b>

Не удалось найти вопрос в базе""")
        logger.error(f"Не удалось найти тему {message.message_thread_id}")


@user_dialog_router.message(ActiveQuestion())
async def active_question(message: Message, stp_db, active_dialog_token: str = None):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        dialog: Question = await repo.dialogs.get_question(token=active_dialog_token)

    if message.text == "✅️ Закрыть вопрос":
        await active_question_end(message, stp_db, active_dialog_token)
        return

    # Перезапускаем таймер неактивности при сообщении от пользователя
    if config.tg_bot.activity_status:
        restart_inactivity_timer(dialog.Token, message.bot, stp_db)

    await message.bot.copy_message(from_chat_id=message.chat.id, message_id=message.message_id,
                                   chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId)


@user_dialog_router.callback_query(QuestionQualitySpecialist.filter(F.return_dialog == True))
async def return_dialog_by_employee(callback: CallbackQuery, callback_data: QuestionQualitySpecialist, stp_db):
    await callback.answer()
    async with stp_db() as session:
        repo = RequestsRepo(session)
        employee: User = await repo.users.get_user(user_id=callback.from_user.id)
        dialog: Question = await repo.dialogs.get_question(token=callback_data.token)

    active_dialogs = await repo.dialogs.get_active_questions()

    if dialog.Status == "closed" and employee.FIO not in [d.EmployeeFullname for d in active_dialogs]:
        await repo.dialogs.update_question_status(token=dialog.Token, status="open")
        await callback.bot.edit_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId,
                                            name=employee.FIO, icon_custom_emoji_id=dicts.topicEmojis["open"])
        await callback.bot.reopen_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId)

        await callback.message.answer(f"""<b>🔓 Вопрос переоткрыт</b>

Можешь писать сообщения, они будут переданы старшему""", reply_markup=finish_question_kb())
        await callback.bot.send_message(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId, text=f"""<b>🔓 Вопрос переоткрыт</b>

Специалист <b>{employee.FIO}</b> переоткрыл вопрос после его закрытия""")
    elif employee.FIO in [d.EmployeeFullname for d in active_dialogs]:
        await callback.answer("У тебя есть другой открытый вопрос", show_alert=True)
    elif dialog.Status != "closed":
        await callback.answer("Этот вопрос не закрыт", show_alert=True)


@user_dialog_router.callback_query(QuestionQualitySpecialist.filter())
async def dialog_quality_employee(callback: CallbackQuery, callback_data: QuestionQualitySpecialist, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)

    await repo.dialogs.update_question_quality(token=callback_data.token, quality=callback_data.answer, is_duty=False)
    await callback.answer("Оценка успешно выставлена ❤️")
    if callback_data.answer:
        await callback.message.edit_text(f"""<b>🔒 Вопрос закрыт</b>

Ты поставил оценку:
👍 Старший <b>помог решить твой вопрос</b>""", reply_markup=closed_dialog_kb(token=callback_data.token, role="employee"))
    else:
        await callback.message.edit_text(f"""<b>🔒 Вопрос закрыт</b>

Ты поставил оценку:
👎 Старший <b>не помог решить твой вопрос</b>""",
                                         reply_markup=closed_dialog_kb(token=callback_data.token, role="employee"))
