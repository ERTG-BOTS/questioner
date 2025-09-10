import datetime
import logging

import pytz
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Question, User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.keyboards.user.main import (
    AskQuestionMenu,
    CancelQuestion,
    MainMenu,
    activity_status_toggle_kb,
    back_kb,
    cancel_question_kb,
    question_ask_kb,
    user_kb,
)
from tgbot.misc.helpers import disable_previous_buttons, extract_clever_link, short_name
from tgbot.misc.states import AskQuestion
from tgbot.services.g_sheets import get_target_forum
from tgbot.services.logger import setup_logging
from tgbot.services.scheduler import (
    remove_question_timer,
    start_attention_reminder,
    start_inactivity_timer,
)

user_router = Router()
user_router.message.filter(F.chat.type == "private")
user_router.callback_query.filter(F.message.chat.type == "private")


setup_logging()
logger = logging.getLogger(__name__)


@user_router.message(CommandStart())
async def main_cmd(
    message: Message, state: FSMContext, user: User, questions_repo: RequestsRepo
):
    employee_topics_today = await questions_repo.questions.get_questions_count_today(
        employee_fullname=user.FIO
    )
    employee_topics_month = (
        await questions_repo.questions.get_questions_count_last_month(
            employee_fullname=user.FIO
        )
    )

    state_data = await state.get_data()
    await state.clear()

    if user:
        await message.answer(
            f"""👋 Привет, <b>{short_name(user.FIO)}</b>!

Я - бот-вопросник

<b>❓ Ты задал вопросов:</b>
- За день {employee_topics_today}
- За месяц {employee_topics_month}

<i>Используй меню для управление ботом</i>""",
            reply_markup=user_kb(
                is_role_changed=True
                if state_data.get("role") or user.Role == 10
                else False
            ),
        )
        logging.info(
            f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {message.from_user.username} ({message.from_user.id}): Открыто юзер-меню"
        )
    else:
        await message.answer(f"""Привет, <b>@{message.from_user.username}</b>!
        
Не нашел тебя в списке зарегистрированных пользователей

Регистрация происходит через бота Графиков
Если возникли сложности с регистраций обратись к МиП

Если ты зарегистрировался недавно, напиши <b>/start</b>""")


@user_router.callback_query(MainMenu.filter(F.menu == "main"))
async def main_cb(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    questions_repo: RequestsRepo,
):
    employee_topics_today = await questions_repo.questions.get_questions_count_today(
        employee_fullname=user.FIO
    )
    employee_topics_month = (
        await questions_repo.questions.get_questions_count_last_month(
            employee_fullname=user.FIO
        )
    )

    state_data = await state.get_data()

    await callback.message.edit_text(
        f"""Привет, <b>{short_name(user.FIO)}</b>!

Я - бот-вопросник

<b>❓ Ты задал вопросов:</b>
- За день {employee_topics_today}
- За месяц {employee_topics_month}

Используй меню, чтобы выбрать действие""",
        reply_markup=user_kb(
            is_role_changed=True if state_data.get("role") or user.Role == 10 else False
        ),
    )
    logging.info(
        f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {callback.from_user.username} ({callback.from_user.id}): Открыто юзер-меню"
    )
    await callback.answer()


@user_router.callback_query(MainMenu.filter(F.menu == "ask"))
async def ask_question(
    callback: CallbackQuery, state: FSMContext, user: User, questions_repo: RequestsRepo
):
    active_questions = await questions_repo.questions.get_active_questions()
    if user.FIO in [d.employee_fullname for d in active_questions]:
        await callback.answer("У тебя есть другой открытый вопрос", show_alert=True)
        return

    state_data = await state.get_data()

    msg = await callback.message.edit_text(
        """<b>🤔 Суть вопроса</b>

Отправь вопрос и вложения одним сообщением""",
        reply_markup=back_kb(),
    )

    await state.update_data(messages_with_buttons=[msg.message_id])
    await state.set_state(AskQuestion.question)
    logging.info(
        f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} [{user.Division}] {callback.from_user.username} ({callback.from_user.id}): Открыто меню нового вопроса"
    )
    await callback.answer()


@user_router.message(AskQuestion.question)
async def question_text(
    message: Message,
    state: FSMContext,
    user: User,
    questions_repo: RequestsRepo,
    main_repo: RequestsRepo,
):
    active_questions = await questions_repo.questions.get_active_questions()
    if user.FIO in [q.employee_fullname for q in active_questions]:
        await state.clear()
        await message.answer("У тебя уже есть активный вопрос")
        return

    question_text = message.caption if message.caption else message.text

    if not question_text or question_text.strip() == "":
        await message.answer("❌ Вопрос не может быть пустым. Отправь текст вопроса.")
        return

    await state.update_data(question=question_text)
    
    has_clever_link = False
    if question_text and "https://clever.ertelecom.ru/content/space/" in question_text:
        extracted_link = extract_clever_link(question_text)
        if extracted_link:
            forbidden_links = [
                "https://clever.ertelecom.ru/content/space/4/wiki/1808/page/0",
                "https://clever.ertelecom.ru/content/space/4/wiki/10259/page/0", 
                "https://clever.ertelecom.ru/content/space/4",
                "https://clever.ertelecom.ru/content/space/4/"
            ]
            has_clever_link = extracted_link not in forbidden_links
    await state.update_data(question_message_id=message.message_id)

    state_data = await state.get_data()
    temp_division = state_data.get("temp_division")
    if state_data.get("processing"):
        return

    await state.update_data(processing=True)

    target_forum_id = await get_target_forum(
        username=user.Username, division=user.Division, temp_division=temp_division
    )
    group_settings = await questions_repo.settings.get_settings_by_group_id(
        group_id=target_forum_id
    )

    ask_clever_link: bool = group_settings.get_setting("ask_clever_link")

    # Если ссылка на регламент уже есть в тексте, пользователь root, или отключен запрос ссылки
    if has_clever_link or user.Role == 10 or not ask_clever_link:
        # Извлекаем ссылку если она есть, иначе None
        clever_link = (
            extract_clever_link(message.text or message.caption)
            if has_clever_link
            else None
        )

        message_content = message.text or message.caption
        if message_content == clever_link:
            await state.update_data(processing=False)
            return

        employee_topics_today = (
            await questions_repo.questions.get_questions_count_today(
                employee_fullname=user.FIO
            )
        )
        employee_topics_month = (
            await questions_repo.questions.get_questions_count_last_month(
                employee_fullname=user.FIO
            )
        )

        new_topic = await message.bot.create_forum_topic(
            chat_id=target_forum_id,
            name=f"{user.Division} | {short_name(user.FIO)}"
            if group_settings.get_setting("show_division")
            else short_name(user.FIO),
            icon_custom_emoji_id=group_settings.get_setting("emoji_open"),
        )  # Создание темы

        new_question = await questions_repo.questions.add_question(
            group_id=target_forum_id,
            topic_id=new_topic.message_thread_id,
            employee_chat_id=message.chat.id,
            employee_fullname=user.FIO,
            employee_division=user.Division,
            start_time=datetime.datetime.now(tz=pytz.timezone("Asia/Yekaterinburg")),
            question_text=state_data.get("question"),
            clever_link=clever_link,  # Может быть None если ссылки нет
            activity_status_enabled=group_settings.get_setting("activity_status"),
        )  # Добавление вопроса в БД

        await message.answer(
            """<b>✅ Успешно</b>

Вопрос передан на рассмотрение, в скором времени тебе ответят""",
            reply_markup=cancel_question_kb(token=new_question.token),
        )

        if user.Username:
            user_fullname = f"<a href='t.me/{user.Username}'>{short_name(user.FIO)}</a>"
        else:
            user_fullname = short_name(user.FIO)

        head = await main_repo.users.get_user(fullname=user.Boss)
        if head.Username:
            head_fullname = f"<a href='t.me/{head.Username}'>{short_name(head.FIO)}</a>"
        else:
            head_fullname = short_name(head.FIO)

        # Формируем текст сообщения в зависимости от наличия ссылки на регламент
        if clever_link:
            topic_text = f"""Вопрос задает <b>{user_fullname}</b>

<blockquote expandable><b>👔 Должность:</b> {user.Position}
<b>👑 Руководитель:</b> {head_fullname}

<b>❓ Вопросов:</b> за день {employee_topics_today} / за месяц {employee_topics_month}</blockquote>"""
        else:
            topic_text = f"""Вопрос задает <b>{user_fullname}</b>

<blockquote expandable><b>👔 Должность:</b> {user.Position}
<b>👑 Руководитель:</b> {head_fullname}

<b>❓ Вопросов:</b> за день {employee_topics_today} / за месяц {employee_topics_month}</blockquote>"""

        topic_info_msg = await message.bot.send_message(
            chat_id=new_question.group_id,
            message_thread_id=new_topic.message_thread_id,
            text=topic_text,
            disable_web_page_preview=True,
            reply_markup=activity_status_toggle_kb(
                token=new_question.token,
                clever_link=clever_link if clever_link else None,
                current_status=new_question.activity_status_enabled,
                global_status=group_settings.get_setting("activity_status"),
            ),
        )

        await message.bot.copy_message(
            chat_id=new_question.group_id,
            message_thread_id=new_topic.message_thread_id,
            from_chat_id=message.chat.id,
            message_id=state_data.get("question_message_id"),
        )  # Копирование сообщения специалиста в тему

        await message.bot.pin_chat_message(
            chat_id=new_question.group_id,
            message_id=topic_info_msg.message_id,
            disable_notification=True,
        )  # Пин информации о специалисте

        await start_attention_reminder(new_question.token, questions_repo)
        await state.clear()
        logging.info(
            f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {message.from_user.username} ({message.from_user.id}): Создан новый вопрос {new_question.token}"
        )
        # Отключаем кнопки на предыдущих шагах
        await disable_previous_buttons(message, state)
        return

    # Отключаем кнопки на предыдущих шагах
    await disable_previous_buttons(message, state)

    # TODO Вернуть проверку на топ юзеров после обсуждения
    # top_users: Sequence[
    #     User
    # ] = await questions_repo.questions.get_top_users_by_division(
    #     division="НЦК" if "НЦК" in user.Division else "НТП", main_repo=main_repo
    # )

    # Если дошли до сюда, значит нужно запросить ссылку на регламент
    response_msg = await message.answer(
        """<b>🗃️ Регламент</b>

Прикрепи ссылку на регламент из клевера, по которому у тебя вопрос""",
        reply_markup=question_ask_kb(is_user_in_top=True),
        # reply_markup=question_ask_kb(
        #     is_user_in_top=True
        #     if user.ChatId in (u.ChatId for u in top_users)
        #     else False
        # ),
    )

    messages_with_buttons = state_data.get("messages_with_buttons", [])
    messages_with_buttons.append(response_msg.message_id)
    await state.update_data(messages_with_buttons=messages_with_buttons)

    await state.set_state(AskQuestion.clever_link)
    logging.info(
        f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {message.from_user.username} ({message.from_user.id}): Открыто меню уточнения регламента"
    )


@user_router.message(AskQuestion.clever_link)
async def clever_link_handler(
    message: Message,
    state: FSMContext,
    user: User,
    questions_repo: RequestsRepo,
    main_repo: RequestsRepo,
):
    active_questions = await questions_repo.questions.get_active_questions()
    if user.FIO in [q.employee_fullname for q in active_questions]:
        await state.clear()
        await message.answer("У тебя уже есть активный вопрос")
        return

    state_data = await state.get_data()

    # Проверяем есть ли ссылка на Клевер в сообщении специалиста или является ли пользователь Рутом
    if (
        "https://clever.ertelecom.ru/content/space/" not in message.text
        and user.Role != 10
    ):
        await message.answer(
            """<b>🗃️ Регламент</b>

Сообщение <b>не содержит ссылку на клевер</b> 🥺

Отправь ссылку на регламент из клевера, по которому у тебя вопрос""",
            reply_markup=back_kb(),
        )
        return

    # Проверяем на запрещенные ссылки
    extracted_link = extract_clever_link(message.text)
    if extracted_link and user.Role != 10:
        forbidden_links = [
            "https://clever.ertelecom.ru/content/space/4/wiki/1808/page/0",
            "https://clever.ertelecom.ru/content/space/4/wiki/10259/page/0", 
            "https://clever.ertelecom.ru/content/space/4",
            "https://clever.ertelecom.ru/content/space/4/"
        ]
        if extracted_link in forbidden_links:
            await message.answer(
                """<b>🗃️ Регламент</b>

Сообщение <b>содержит запрещенную ссылку</b> 🥺

Отправь корректную ссылку на регламент из клевера, по которому у тебя вопрос""",
                reply_markup=back_kb(),
            )
            return

    clever_link = extracted_link
    await state.clear()
    employee_topics_today = await questions_repo.questions.get_questions_count_today(
        employee_fullname=user.FIO
    )
    employee_topics_month = (
        await questions_repo.questions.get_questions_count_last_month(
            employee_fullname=user.FIO
        )
    )

    target_forum_id = await get_target_forum(
        username=user.Username, division=user.Division
    )
    group_settings = await questions_repo.settings.get_settings_by_group_id(
        group_id=target_forum_id
    )

    # Выключаем все предыдущие кнопки
    await disable_previous_buttons(message, state)

    new_topic = await message.bot.create_forum_topic(
        chat_id=target_forum_id,
        name=f"{user.Division} | {short_name(user.FIO)}"
        if group_settings.get_setting("show_division")
        else short_name(user.FIO),
        icon_custom_emoji_id=group_settings.get_setting("emoji_open"),
    )  # Создание темы

    new_question = await questions_repo.questions.add_question(
        group_id=target_forum_id,
        topic_id=new_topic.message_thread_id,
        employee_chat_id=message.chat.id,
        employee_fullname=user.FIO,
        employee_division=user.Division,
        start_time=datetime.datetime.now(tz=pytz.timezone("Asia/Yekaterinburg")),
        question_text=state_data.get("question"),
        clever_link=clever_link if clever_link else None,
        activity_status_enabled=group_settings.get_setting("activity_status"),
    )  # Добавление вопроса в БД

    await message.answer(
        """<b>✅ Успешно</b>

Вопрос передан на рассмотрение, в скором времени тебе ответят""",
        reply_markup=cancel_question_kb(token=new_question.token),
    )

    if user.Username:
        user_fullname = f"<a href='t.me/{user.Username}'>{short_name(user.FIO)}</a>"
    else:
        user_fullname = short_name(user.FIO)

    head = await main_repo.users.get_user(fullname=user.Boss)
    if head.Username:
        head_fullname = f"<a href='t.me/{head.Username}'>{short_name(head.FIO)}</a>"
    else:
        head_fullname = short_name(head.FIO)

    topic_info_msg = await message.bot.send_message(
        chat_id=target_forum_id,
        message_thread_id=new_topic.message_thread_id,
        text=f"""Вопрос задает <b>{user_fullname}</b>

<blockquote expandable><b>👔 Должность:</b> {user.Position}
<b>👑 Руководитель:</b> {head_fullname}

<b>❓ Вопросов:</b> за день {employee_topics_today} / за месяц {employee_topics_month}</blockquote>""",
        disable_web_page_preview=True,
        reply_markup=activity_status_toggle_kb(
            token=new_question.token,
            clever_link=clever_link if clever_link else None,
            current_status=new_question.activity_status_enabled,
            global_status=group_settings.get_setting("activity_status"),
        ),
    )

    await message.bot.copy_message(
        chat_id=new_question.group_id,
        message_thread_id=new_topic.message_thread_id,
        from_chat_id=message.chat.id,
        message_id=state_data.get("question_message_id"),
    )  # Копирование сообщения специалиста в тему

    await message.bot.pin_chat_message(
        chat_id=new_question.group_id,
        message_id=topic_info_msg.message_id,
        disable_notification=True,
    )  # Пин информации о специалисте

    await start_attention_reminder(new_question.token, questions_repo)
    logging.info(
        f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {message.from_user.username} ({message.from_user.id}): Создан новый вопрос {new_question.token}"
    )


@user_router.callback_query(AskQuestionMenu.filter(not F.found_regulation))
async def regulation_not_found_handler(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    questions_repo: RequestsRepo,
    main_repo: RequestsRepo,
):
    """
    Обработчик кнопки "Не нашел" для случая, когда пользователь не смог найти регламент
    """
    state_data = await state.get_data()
    await state.clear()

    # Получаем статистику для пользователя
    employee_topics_today = await questions_repo.questions.get_questions_count_today(
        employee_fullname=user.FIO
    )
    employee_topics_month = (
        await questions_repo.questions.get_questions_count_last_month(
            employee_fullname=user.FIO
        )
    )

    target_forum_id = await get_target_forum(
        username=user.Username, division=user.Division
    )
    group_settings = await questions_repo.settings.get_settings_by_group_id(
        group_id=target_forum_id
    )

    # Отключаем кнопки на предыдущих шагах
    await disable_previous_buttons(callback.message, state)

    # Создаем новую тему
    new_topic = await callback.bot.create_forum_topic(
        chat_id=target_forum_id,
        name=f"{user.Division} | {short_name(user.FIO)}"
        if group_settings.get_setting("show_division")
        else short_name(user.FIO),
        icon_custom_emoji_id=group_settings.get_setting("emoji_open"),
    )

    # Создаем новый вопрос с clever_link = "не нашел"
    new_question = await questions_repo.questions.add_question(
        group_id=target_forum_id,
        topic_id=new_topic.message_thread_id,
        employee_chat_id=callback.from_user.id,
        employee_fullname=user.FIO,
        employee_division=user.Division,
        start_time=datetime.datetime.now(tz=pytz.timezone("Asia/Yekaterinburg")),
        question_text=state_data.get("question"),
        clever_link="не нашел",  # Устанавливаем специальное значение,
        activity_status_enabled=group_settings.get_setting("activity_status"),
    )

    # Отправляем сообщение об успехе
    await callback.message.edit_text(
        """<b>✅ Успешно</b>

Вопрос передан на рассмотрение, в скором времени тебе ответят""",
        reply_markup=cancel_question_kb(token=new_question.token),
    )

    # Запускаем таймер бездействия для нового вопроса
    if new_question.status == "open" and new_question.activity_status_enabled:
        await start_inactivity_timer(new_question.token, questions_repo)

    if user.Username:
        user_fullname = f"<a href='t.me/{user.Username}'>{short_name(user.FIO)}</a>"
    else:
        user_fullname = short_name(user.FIO)

    head = await main_repo.users.get_user(fullname=user.Boss)
    if head.Username:
        head_fullname = f"<a href='t.me/{head.Username}'>{short_name(head.FIO)}</a>"
    else:
        head_fullname = short_name(head.FIO)

    # Формируем текст сообщения с указанием "не нашел" в регламенте
    topic_text = f"""Вопрос задает <b>{user_fullname}</b>

Специалист не нашел регламент

<blockquote expandable><b>👔 Должность:</b> {user.Position}
<b>👑 Руководитель:</b> {head_fullname}

<b>❓ Вопросов:</b> за день {employee_topics_today} / за месяц {employee_topics_month}</blockquote>"""

    # Отправляем информацию в тему
    topic_info_msg = await callback.bot.send_message(
        chat_id=new_question.group_id,
        message_thread_id=new_topic.message_thread_id,
        text=topic_text,
        disable_web_page_preview=True,
        reply_markup=activity_status_toggle_kb(
            token=new_question.token,
            current_status=new_question.activity_status_enabled,
            global_status=group_settings.get_setting("activity_status"),
        ),
    )

    # Копируем оригинальное сообщение с вопросом
    await callback.bot.copy_message(
        chat_id=new_question.group_id,
        message_thread_id=new_topic.message_thread_id,
        from_chat_id=callback.message.chat.id,
        message_id=state_data.get("question_message_id"),
    )

    # Закрепляем информационное сообщение
    await callback.bot.pin_chat_message(
        chat_id=new_question.group_id,
        message_id=topic_info_msg.message_id,
        disable_notification=True,
    )

    # Очищаем состояние
    await callback.answer()

    await start_attention_reminder(new_question.token, questions_repo)

    logging.info(
        f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {callback.from_user.username} ({callback.from_user.id}): Создан новый вопрос {new_question.token} без регламента (не нашел)"
    )


@user_router.callback_query(CancelQuestion.filter(F.action == "cancel"))
async def cancel_question(
    callback: CallbackQuery,
    callback_data: CancelQuestion,
    state: FSMContext,
    questions_repo: RequestsRepo,
    user: User,
):
    question: Question = await questions_repo.questions.get_question(
        token=callback_data.token
    )

    if (
        question
        and question.status == "open"
        and not question.topic_duty_fullname
        and not question.end_time
    ):
        group_settings = await questions_repo.settings.get_settings_by_group_id(
            group_id=question.group_id
        )

        await callback.bot.edit_forum_topic(
            chat_id=question.group_id,
            message_thread_id=question.topic_id,
            icon_custom_emoji_id=group_settings.get_setting("emoji_fired"),
        )
        await callback.bot.close_forum_topic(
            chat_id=question.group_id,
            message_thread_id=question.topic_id,
        )
        await questions_repo.questions.delete_question(token=question.token)
        await remove_question_timer(question=question)
        await callback.bot.send_message(
            chat_id=question.group_id,
            message_thread_id=question.topic_id,
            text="""<b>🔥 Отмена вопроса</b>
        
Специалист отменил вопрос

<i>Вопрос будет удален через 30 секунд</i>""",
        )
        await callback.answer("Вопрос успешно удален")
        await main_cb(
            callback=callback, state=state, user=user, questions_repo=questions_repo
        )
    elif not question:
        await callback.answer("Не удалось найти отменяемый вопрос")
        await main_cb(
            callback=callback, state=state, user=user, questions_repo=questions_repo
        )
    else:
        await callback.answer("Вопрос не может быть отменен. Он уже в работе")
    await callback.answer()


@user_router.message()
async def default_message_handler(
    message: Message, state: FSMContext, user: User, questions_repo: RequestsRepo
):
    """
    Default handler for all unhandled user messages.
    Sends start message if user is not in question state and doesn't have active questions.
    """
    # Проверяем FSM
    current_state = await state.get_state()

    logger.info(current_state)
    # Пропускаем если у пользователя есть состояние
    if current_state is not None:
        return

    # Проверяем есть ли у пользователя активные вопросы
    try:
        active_questions = await questions_repo.questions.get_active_questions()
        logger.info(active_questions)
        if user.FIO in [q.employee_fullname for q in active_questions]:
            return
    except Exception as e:
        logger.error(f"Error checking active questions for user {user.FIO}: {e}")
        return

    # Если мы оказались здесь - у пользователя нет активных вопросов и состояний в FSM
    # Отправляем стартовое сообщение
    employee_topics_today = await questions_repo.questions.get_questions_count_today(
        employee_fullname=user.FIO
    )
    employee_topics_month = (
        await questions_repo.questions.get_questions_count_last_month(
            employee_fullname=user.FIO
        )
    )

    await message.answer(
        f"""👋 Привет, <b>{short_name(user.FIO)}</b>!

Я - бот-вопросник

<b>❓ Ты задал вопросов:</b>
- За день {employee_topics_today}
- За месяц {employee_topics_month}

<i>Используй меню для управление ботом</i>""",
        reply_markup=user_kb(is_role_changed=user.Role == 10),
    )

    logging.info(
        f"[Дефолт] {message.from_user.username} ({message.from_user.id}): Отправлено стартовое сообщение"
    )
