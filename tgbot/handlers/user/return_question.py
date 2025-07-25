import logging
from typing import Sequence

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from infrastructure.database.models import Question, User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.keyboards.group.main import reopened_question_kb
from tgbot.keyboards.user.main import (
    MainMenu,
    QuestionQualitySpecialist,
    ReturnQuestion,
    back_kb,
    finish_question_kb,
    question_confirm_kb,
    questions_list_kb,
    user_kb,
)
from tgbot.misc import dicts
from tgbot.services.logger import setup_logging

employee_return_q = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@employee_return_q.callback_query(QuestionQualitySpecialist.filter(F.return_question))
async def return_finished_q(
    callback: CallbackQuery,
    callback_data: QuestionQualitySpecialist,
    state: FSMContext,
    questions_repo: RequestsRepo,
    main_repo: RequestsRepo,
    user: User,
):
    """
    Возврат вопроса специалистом по клику на клавиатуру после закрытия вопроса.
    """
    await state.clear()

    active_questions: Sequence[
        Question
    ] = await questions_repo.questions.get_active_questions()
    question: Question = await questions_repo.questions.get_question(
        callback_data.token
    )
    available_to_return_questions: Sequence[
        Question
    ] = await questions_repo.questions.get_available_to_return_questions()

    if (
        question.status == "closed"
        and user.FIO not in [d.employee_fullname for d in active_questions]
        and question.token in [d.token for d in available_to_return_questions]
    ):
        duty: User = await main_repo.users.get_user(
            fullname=question.topic_duty_fullname
        )
        await questions_repo.questions.update_question_status(
            token=question.token, status="open"
        )

        await callback.bot.edit_forum_topic(
            chat_id=config.tg_bot.forum_id,
            message_thread_id=question.topic_id,
            name=user.FIO
            if config.tg_bot.division == "НЦК"
            else f"{user.Division} | {user.FIO}",
            icon_custom_emoji_id=dicts.topicEmojis["in_progress"],
        )
        await callback.bot.reopen_forum_topic(
            chat_id=config.tg_bot.forum_id, message_thread_id=question.topic_id
        )

        await callback.message.answer(
            """<b>🔓 Вопрос переоткрыт</b>

Можешь писать сообщения, они будут переданы старшему""",
            reply_markup=finish_question_kb(),
        )
        await callback.bot.send_message(
            chat_id=config.tg_bot.forum_id,
            message_thread_id=question.topic_id,
            text=f"""<b>🔓 Вопрос переоткрыт</b>

Специалист <b>{user.FIO}</b> переоткрыл вопрос сразу после закрытия

<b>👮‍♂️ Старший:</b> {duty.FIO} {'(<a href="https://t.me/' + duty.Username + '">лс</a>)' if (duty.Username != "Не указан" or duty.Username != "Скрыто/не определено") else ""}

<b>❓ Изначальный вопрос:</b>
<blockquote expandable><i>{question.question_text}</i></blockquote>""",
            reply_markup=reopened_question_kb(),
            disable_web_page_preview=True,
        )
        logger.info(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Вопрос {question.token} переоткрыт специалистом"
        )
    elif user.FIO in [d.employee_fullname for d in active_questions]:
        await callback.answer("У тебя есть другой открытый вопрос", show_alert=True)
        logger.info(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия, у специалиста есть другой открытый вопрос"
        )
    elif question.status != "closed":
        await callback.answer("Этот вопрос не закрыт", show_alert=True)
        logger.error(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия, диалог {question.token} не закрыт"
        )
    elif question.token not in [d.token for d in available_to_return_questions]:
        await callback.answer(
            "Вопрос не переоткрыть. Прошло более 24 часов или возврат заблокирован",
            show_alert=True,
        )
        logger.error(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия, диалог {question.token} был закрыт более 24 часов назад или заблокирован"
        )


@employee_return_q.callback_query(MainMenu.filter(F.menu == "return"))
async def q_list(
    callback: CallbackQuery, state: FSMContext, user: User, questions_repo: RequestsRepo
):
    """
    Меню "🔄 Возврат вопроса". Отображает последние 5 закрытых вопросов за последние 24 часа для возврата в работу со стороны специалиста.
    """
    questions: Sequence[
        Question
    ] = await questions_repo.questions.get_last_questions_by_chat_id(
        employee_chat_id=callback.from_user.id, limit=5
    )

    state_data = await state.get_data()
    if not questions:
        await callback.message.edit_text(
            """<b>🔄 Возврат вопроса</b>

📝 У тебя нет закрытых вопросов за последние 24 часа""",
            reply_markup=back_kb(),
        )
        logging.warning(
            f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {callback.from_user.username} ({callback.from_user.id}): Открыто меню возврата чата, доступных вопросов нет"
        )
        return

    await callback.message.edit_text(
        """<b>🔄 Возврат вопроса</b>

📋 Выбери вопрос из списка доступных

<i>Отображаются вопросы, закрытые за последние 24 часа</i>""",
        reply_markup=questions_list_kb(questions),
    )
    logging.info(
        f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {callback.from_user.username} ({callback.from_user.id}): Открыто меню возврата чата"
    )


@employee_return_q.callback_query(ReturnQuestion.filter(F.action == "show"))
async def q_info(
    callback: CallbackQuery,
    callback_data: ReturnQuestion,
    state: FSMContext,
    user: User,
    questions_repo: RequestsRepo,
    main_repo: RequestsRepo,
):
    """Меню описания выбранного специалистом вопроса для возврата в работу"""
    question: Question = await questions_repo.questions.get_question(
        token=callback_data.token
    )

    if not question:
        await callback.message.edit_text("❌ Вопрос не найден", reply_markup=user_kb())
        return

    duty: User = await main_repo.users.get_user(fullname=question.topic_duty_fullname)

    state_data = await state.get_data()
    start_date_str = question.start_time.strftime("%d.%m.%Y %H:%M")
    end_date_str = (
        question.end_time.strftime("%d.%m.%Y %H:%M")
        if question.end_time
        else "Не указано"
    )
    question_text = (
        question.question_text[:200] + "..."
        if len(question.question_text) > 200
        else question.question_text
    )

    await callback.message.edit_text(
        f"""<b>🔄 Возврат вопроса</b>

❓ <b>Вопрос:</b>
<blockquote expandable>{question_text}</blockquote>

🗃️ <b>Регламент:</b> <a href='{question.clever_link}'>тык</a>

<b>👮‍♂️ Старший:</b> {duty.FIO} {'(<a href="https://t.me/' + duty.Username + '">лс</a>)' if (duty.Username != "Не указан" or duty.Username != "Скрыто/не определено") else ""}
🚀 <b>Дата создания:</b> {start_date_str}
🔒 <b>Дата закрытия:</b> {end_date_str}

Хочешь вернуть этот вопрос?""",
        reply_markup=question_confirm_kb(question.token),
        disable_web_page_preview=True,
    )
    logging.warning(
        f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {callback.from_user.username} ({callback.from_user.id}): Открыто описание вопроса {question.token} для возврата"
    )
    await callback.answer()


@employee_return_q.callback_query(ReturnQuestion.filter(F.action == "confirm"))
async def return_q_confirm(
    callback: CallbackQuery,
    callback_data: ReturnQuestion,
    state: FSMContext,
    user: User,
    questions_repo: RequestsRepo,
    main_repo: RequestsRepo,
):
    """Возврат выбранного специалистом вопроса в работу"""
    await state.clear()

    question: Question = await questions_repo.questions.get_question(
        token=callback_data.token
    )

    if not question:
        await callback.message.edit_text("❌ Вопрос не найден", reply_markup=user_kb())
        return

    active_questions = await questions_repo.questions.get_active_questions()

    if (
        question.status == "closed"
        and user.FIO not in [d.employee_fullname for d in active_questions]
        and question.allow_return
    ):
        duty: User = await main_repo.users.get_user(
            fullname=question.topic_duty_fullname
        )
        # 1. Обновляем статус вопроса на "open"
        await questions_repo.questions.update_question_status(
            token=question.token, status="open"
        )

        # 2. Обновляем название и иконку темы
        await callback.bot.edit_forum_topic(
            chat_id=config.tg_bot.forum_id,
            message_thread_id=question.topic_id,
            name=user.FIO
            if config.tg_bot.division == "НЦК"
            else f"{user.Division} | {user.FIO}",
            icon_custom_emoji_id=dicts.topicEmojis["in_progress"],
        )

        # 3. Переоткрываем тему
        await callback.bot.reopen_forum_topic(
            chat_id=config.tg_bot.forum_id, message_thread_id=question.topic_id
        )

        # 4. Отправляем подтверждающее сообщение специалисту
        await callback.message.answer(
            """<b>🔓 Вопрос переоткрыт</b>

Можешь писать сообщения, они будут переданы старшему""",
            reply_markup=finish_question_kb(),
        )

        # 5. Отправляем уведомление дежурному в тему
        await callback.bot.send_message(
            chat_id=config.tg_bot.forum_id,
            message_thread_id=question.topic_id,
            text=f"""<b>🔓 Вопрос переоткрыт</b>

Специалист <b>{user.FIO}</b> переоткрыл вопрос из истории вопросов

<b>👮‍♂️ Старший:</b> {duty.FIO} {'(<a href="https://t.me/' + duty.Username + '">лс</a>)' if (duty.Username != "Не указан" or duty.Username != "Скрыто/не определено") else ""}

<b>❓ Изначальный вопрос:</b>
<blockquote expandable><i>{question.question_text}</i></blockquote>""",
            reply_markup=reopened_question_kb(),
            disable_web_page_preview=True,
        )
    elif user.FIO in [d.employee_fullname for d in active_questions]:
        # Проверка на наличие открытых вопросов у специалиста
        await callback.answer("У тебя есть другой открытый вопрос", show_alert=True)
        logger.error(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия, у специалиста {question.employee_fullname} есть другой открытый вопрос"
        )
    elif question.status != "closed":
        # Проверка на закрытость вопроса
        await callback.answer("Этот вопрос не закрыт", show_alert=True)
        logger.error(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия, вопрос {question.token} не закрыт"
        )
    elif not question.allow_return:
        # Проверка на доступность возврата вопроса
        await callback.answer("Возврат вопроса заблокирован", show_alert=True)
        logger.error(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия, вопрос {question.token} заблокирован для возврата"
        )
    else:
        await callback.answer("Не удалось переоткрыть вопрос", show_alert=True)
        logger.error(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия вопроса {question.token}"
        )
    await callback.answer()
