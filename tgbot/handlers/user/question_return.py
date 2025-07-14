import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.keyboards.user.main import user_kb, MainMenu, ReturnQuestion, questions_list_kb, \
    question_confirm_kb
from tgbot.misc import dicts
from tgbot.services.logger import setup_logging

user_return_question_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@user_return_question_router.callback_query(MainMenu.filter(F.menu == "return"))
async def return_question_list(callback: CallbackQuery, stp_db):
    """Показать список последних 5 вопросов пользователя за 24 часа"""
    async with stp_db() as session:
        repo = RequestsRepo(session)
        questions = await repo.dialogs.get_last_questions_by_chat_id(
            employee_chat_id=callback.from_user.id,
            limit=5
        )

    if not questions:
        await callback.message.edit_text(
            """<b>🔄 Возврат вопроса</b>

📝 У тебя нет закрытых вопросов за последние 24 часа""",
            reply_markup=user_kb()
        )
        return

    await callback.message.edit_text(
        """<b>🔄 Возврат вопроса</b>

📋 Выбери вопрос по времени закрытия

<i>Отображаются вопросы, закрытые за последние 24 часа</i>""",
        reply_markup=questions_list_kb(questions)
    )


@user_return_question_router.callback_query(ReturnQuestion.filter(F.action == "show"))
async def return_question_show(callback: CallbackQuery, callback_data: ReturnQuestion, stp_db):
    """Показать текст вопроса и запросить подтверждение"""
    async with stp_db() as session:
        repo = RequestsRepo(session)
        question = await repo.dialogs.get_question(token=callback_data.token)

    if not question:
        await callback.message.edit_text(
            "❌ Вопрос не найден",
            reply_markup=user_kb()
        )
        return

    start_date_str = question.StartTime.strftime("%d.%m.%Y %H:%M")
    end_date_str = question.EndTime.strftime("%d.%m.%Y %H:%M") if question.EndTime else "Не указано"
    question_text = question.QuestionText[:200] + "..." if len(question.QuestionText) > 200 else question.QuestionText

    await callback.message.edit_text(f"""<b>🔄 Возврат вопроса</b>

❓ <b>Вопрос:</b>
<blockquote expandable>{question_text}</blockquote>

🗃️ <b>Регламент:</b> <a href='{question.CleverLink}'>тык</a>

<b>Дата создания:</b> {start_date_str}
🔒 <b>Дата закрытия:</b> {end_date_str}

Хочешь вернуть этот вопрос?""",
                                     reply_markup=question_confirm_kb(question.Token),
                                     disable_web_page_preview=True
                                     )


@user_return_question_router.callback_query(ReturnQuestion.filter(F.action == "confirm"))
async def return_question_confirm(callback: CallbackQuery, callback_data: ReturnQuestion, stp_db):
    """Подтвердить возврат вопроса"""
    await callback.answer()
    async with stp_db() as session:
        repo = RequestsRepo(session)
        user: User = await repo.users.get_user(user_id=callback.from_user.id)
        question = await repo.dialogs.get_question(token=callback_data.token)

    if not question:
        await callback.message.edit_text(
            "❌ Вопрос не найден",
            reply_markup=user_kb()
        )
        return

    active_dialogs = await repo.dialogs.get_active_questions()

    # Validation checks (same as existing restoration logic)
    if question.Status == "closed" and user.FIO not in [d.EmployeeFullname for d in active_dialogs]:
        # 1. Update question status to "open"
        await repo.dialogs.update_question_status(token=question.Token, status="open")

        # 2. Update forum topic name and icon
        await callback.bot.edit_forum_topic(
            chat_id=config.tg_bot.forum_id,
            message_thread_id=question.TopicId,
            name=user.FIO,
            icon_custom_emoji_id=dicts.topicEmojis["in_progress"]
        )

        # 3. Reopen the forum topic
        await callback.bot.reopen_forum_topic(
            chat_id=config.tg_bot.forum_id,
            message_thread_id=question.TopicId
        )

        # 4. Send confirmation messages
        await callback.message.edit_text(f"""<b>🔓 Вопрос переоткрыт</b>

Можешь писать сообщения, они будут переданы старшему""")

        await callback.bot.send_message(
            chat_id=config.tg_bot.forum_id,
            message_thread_id=question.TopicId,
            text=f"""<b>🔓 Вопрос переоткрыт</b>

Специалист <b>{user.FIO}</b> переоткрыл вопрос из истории вопросов"""
        )
    elif user.FIO in [d.EmployeeFullname for d in active_dialogs]:
        await callback.answer("У тебя есть другой открытый вопрос", show_alert=True)
    elif question.Status != "closed":
        await callback.answer("Этот вопрос не закрыт", show_alert=True)
    else:
        await callback.answer("Не удалось переоткрыть вопрос", show_alert=True)
