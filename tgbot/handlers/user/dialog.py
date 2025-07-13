import datetime
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from infrastructure.database.models import User, Dialog
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.active_question import ActiveQuestion, ActiveQuestionWithCommand
from tgbot.keyboards.user.main import DialogQualitySpecialist, dialog_quality_kb
from tgbot.misc import dicts
from tgbot.services.logger import setup_logging

user_dialog_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@user_dialog_router.message(ActiveQuestionWithCommand("end"))
async def active_question_end(message: Message, stp_db, active_dialog_token: str = None):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        employee: User = await repo.users.get_user(message.from_user.id)
        dialog: Dialog = await repo.dialogs.get_dialog(token=active_dialog_token)

    logger.info(active_dialog_token)
    if dialog is not None:
        if dialog.Status != "closed":
            await repo.dialogs.update_dialog_status(token=dialog.Token, status="closed")
            await repo.dialogs.update_dialog_end(token=dialog.Token, end_time=datetime.datetime.now())

            await message.bot.send_message(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId,  text=f"""<b>🔒 Диалог закрыт</b>

Специалист <b>{employee.FIO}</b> закрыл диалог
Оцени, мог ли специалист решить вопрос самостоятельно""", reply_markup=dialog_quality_kb(token=dialog.Token, role="duty"))

            await message.bot.edit_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId,
                                               icon_custom_emoji_id=dicts.topicEmojis["closed"])
            await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId)

            await message.reply(f"""<b>🔒 Диалог закрыт</b>

Ты закрыл диалог
Оцени, помогли ли тебе решить вопрос""", reply_markup=dialog_quality_kb(token=dialog.Token, role="employee"))
        elif dialog.Status == "closed":
            await message.reply("<b>🔒 Диалог был закрыт</b>")
            await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId)

    else:
        await message.answer(f"""<b>⚠️ Ошибка</b>

Не удалось найти вопрос в базе""")
        logger.error(f"Не удалось найти топик {message.message_thread_id}")


@user_dialog_router.message(ActiveQuestion())
async def active_question(message: Message, stp_db, active_dialog_token: str = None):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        dialog: Dialog = await repo.dialogs.get_dialog(token=active_dialog_token)

    await message.bot.copy_message(from_chat_id=message.chat.id, message_id=message.message_id,
                                   chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId)


@user_dialog_router.callback_query(DialogQualitySpecialist.filter())
async def dialog_quality_employee(callback: CallbackQuery, callback_data: DialogQualitySpecialist, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(user_id=callback.from_user.id)

    await repo.dialogs.update_dialog_quality(token=callback_data.token, quality=callback_data.answer, is_duty=False)
    await callback.answer("Оценка успешно выставлена ❤️")
    if callback_data.answer:
        await callback.message.edit_text(f"""<b>🔒 Диалог закрыт</b>

Ты поставил оценку:
👍 Старший <b>помог решить твой вопрос</b>""")
    else:
        await callback.message.edit_text(f"""<b>🔒 Диалог закрыт</b>

Ты поставил оценку:
👎 Старший <b>не помог решить твой вопрос</b>""")
