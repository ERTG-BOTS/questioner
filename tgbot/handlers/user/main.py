import datetime
import logging
from typing import Sequence

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import Question, User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.keyboards.user.main import (
    ActivityStatusToggle,
    AskQuestionMenu,
    CancelQuestion,
    MainMenu,
    activity_status_toggle_kb,
    back_kb,
    cancel_question_kb,
    question_ask_kb,
    user_kb,
)
from tgbot.misc import dicts
from tgbot.misc.helpers import disable_previous_buttons, extract_clever_link
from tgbot.misc.states import AskQuestion
from tgbot.services.logger import setup_logging
from tgbot.services.scheduler import (
    remove_question_timer,
    run_delete_timer,
    start_inactivity_timer,
)

user_router = Router()

config = load_config(".env")

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

    if user:
        await message.answer(
            f"""👋 Привет, <b>{user.FIO}</b>!

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
        f"""Привет, <b>{user.FIO}</b>!

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
        f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {callback.from_user.username} ({callback.from_user.id}): Открыто меню нового вопроса"
    )


@user_router.message(AskQuestion.question)
async def question_text(
    message: Message,
    state: FSMContext,
    user: User,
    questions_repo: RequestsRepo,
    main_repo: RequestsRepo,
):
    if message.caption:
        await state.update_data(question=message.caption)
        has_clever_link = "clever.ertelecom.ru/content/space/" in message.caption
    else:
        await state.update_data(question=message.text)
        has_clever_link = "clever.ertelecom.ru/content/space/" in message.text
    await state.update_data(question_message_id=message.message_id)

    # Отключаем кнопки на предыдущих шагах
    await disable_previous_buttons(message, state)

    state_data = await state.get_data()

    is_root_user = user.Role == 10
    skip_clever_link = not config.tg_bot.ask_clever_link

    # Если ссылка на регламент уже есть в тексте, пользователь root, или отключен запрос ссылки
    if has_clever_link or is_root_user or skip_clever_link:
        # Извлекаем ссылку если она есть, иначе None
        clever_link = extract_clever_link(message.text) if has_clever_link else None

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
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
            name=f"{user.Division} | {user.FIO}"
            if "НТП" in user.Division
            else user.FIO,
            icon_custom_emoji_id=dicts.topicEmojis["open"],
        )  # Создание темы

        new_question = await questions_repo.questions.add_question(
            group_id=int(
                config.tg_bot.ntp_forum_id
                if "НТП" in user.Division
                else config.tg_bot.nck_forum_id
            ),
            topic_id=new_topic.message_thread_id,
            employee_chat_id=message.chat.id,
            employee_fullname=user.FIO,
            employee_division=user.Division,
            start_time=datetime.datetime.now(),
            question_text=state_data.get("question"),
            clever_link=clever_link,  # Может быть None если ссылки нет
        )  # Добавление вопроса в БД

        await message.answer(
            """<b>✅ Успешно</b>

Вопрос передан на рассмотрение, в скором времени тебе ответят""",
            reply_markup=cancel_question_kb(token=new_question.token),
        )

        # Запускаем таймер бездействия для нового вопроса (только если статус "open")
        if new_question.status == "open":
            await start_inactivity_timer(
                new_question.token, message.bot, questions_repo
            )

        # Формируем текст сообщения в зависимости от наличия ссылки на регламент
        if clever_link:
            topic_text = f"""Вопрос задает <b>{user.FIO}</b>

<b>🗃️ Регламент:</b> <a href='{clever_link}'>тык</a>

<blockquote expandable><b>👔 Должность:</b> {user.Position}
<b>👑 Руководитель:</b> {user.Boss}

<b>❓ Вопросов:</b> за день {employee_topics_today} / за месяц {employee_topics_month}</blockquote>"""
        else:
            topic_text = f"""Вопрос задает <b>{user.FIO}</b>

<blockquote expandable><b>👔 Должность:</b> {user.Position}
<b>👑 Руководитель:</b> {user.Boss}

<b>❓ Вопросов:</b> за день {employee_topics_today} / за месяц {employee_topics_month}</blockquote>"""

        topic_info_msg = await message.bot.send_message(
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
            message_thread_id=new_topic.message_thread_id,
            text=topic_text,
            disable_web_page_preview=True,
            reply_markup=activity_status_toggle_kb(
                token=new_question.token,
                user_id=new_question.employee_chat_id,
                current_status=new_question.activity_status_enabled,
                global_status=config.tg_bot.activity_status,
            ),
        )

        await message.bot.copy_message(
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
            message_thread_id=new_topic.message_thread_id,
            from_chat_id=message.chat.id,
            message_id=state_data.get("question_message_id"),
        )  # Копирование сообщения специалиста в тему

        await message.bot.pin_chat_message(
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
            message_id=topic_info_msg.message_id,
            disable_notification=True,
        )  # Пин информации о специалисте

        await state.clear()
        logging.info(
            f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {message.from_user.username} ({message.from_user.id}): Создан новый вопрос {new_question.token}"
        )
        return

    top_users: Sequence[
        User
    ] = await questions_repo.questions.get_top_users_by_division(
        division="НЦК" if "НЦК" in user.Division else "НТП", main_repo=main_repo
    )

    # Если дошли до сюда, значит нужно запросить ссылку на регламент
    response_msg = await message.answer(
        """<b>🗃️ Регламент</b>

Прикрепи ссылку на регламент из клевера, по которому у тебя вопрос""",
        reply_markup=question_ask_kb(
            is_user_in_top=True
            if user.ChatId in (u.ChatId for u in top_users)
            else False
        ),
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
    message: Message, state: FSMContext, user: User, questions_repo: RequestsRepo
):
    clever_link = message.text
    state_data = await state.get_data()

    # Проверяем есть ли ссылка на Клевер в сообщении специалиста или является ли пользователь Рутом
    if "clever.ertelecom.ru/content/space/" not in message.text and user.Role != 10:
        await message.answer(
            """<b>🗃️ Регламент</b>

Сообщение <b>не содержит ссылку на клевер</b> 🥺

Отправь ссылку на регламент из клевера, по которому у тебя вопрос""",
            reply_markup=back_kb(),
        )
        return

    employee_topics_today = await questions_repo.questions.get_questions_count_today(
        employee_fullname=user.FIO
    )
    employee_topics_month = (
        await questions_repo.questions.get_questions_count_last_month(
            employee_fullname=user.FIO
        )
    )

    # Выключаем все предыдущие кнопки
    await disable_previous_buttons(message, state)

    new_topic = await message.bot.create_forum_topic(
        chat_id=config.tg_bot.ntp_forum_id
        if "НТП" in user.Division
        else config.tg_bot.nck_forum_id,
        name=f"{user.Division} | {user.FIO}" if "НТП" in user.Division else user.FIO,
        icon_custom_emoji_id=dicts.topicEmojis["open"],
    )  # Создание темы

    new_question = await questions_repo.questions.add_question(
        group_id=int(
            config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id
        ),
        topic_id=new_topic.message_thread_id,
        employee_chat_id=message.chat.id,
        employee_fullname=user.FIO,
        employee_division=user.Division,
        start_time=datetime.datetime.now(),
        question_text=state_data.get("question"),
        clever_link=clever_link,
    )  # Добавление вопроса в БД

    await message.answer(
        """<b>✅ Успешно</b>

Вопрос передан на рассмотрение, в скором времени тебе ответят""",
        reply_markup=cancel_question_kb(token=new_question.token),
    )

    # Запускаем таймер бездействия для нового вопроса (только если статус "open")
    if new_question.status == "open":
        await start_inactivity_timer(new_question.token, message.bot, questions_repo)

    topic_info_msg = await message.bot.send_message(
        chat_id=config.tg_bot.ntp_forum_id
        if "НТП" in user.Division
        else config.tg_bot.nck_forum_id,
        message_thread_id=new_topic.message_thread_id,
        text=f"""Вопрос задает <b>{user.FIO}</b>

<b>🗃️ Регламент:</b> <a href='{clever_link}'>тык</a>

<blockquote expandable><b>👔 Должность:</b> {user.Position}
<b>👑 Руководитель:</b> {user.Boss}

<b>❓ Вопросов:</b> за день {employee_topics_today} / за месяц {employee_topics_month}</blockquote>""",
        disable_web_page_preview=True,
        reply_markup=activity_status_toggle_kb(
            token=new_question.token,
            user_id=new_question.employee_chat_id,
            current_status=new_question.activity_status_enabled,
            global_status=config.tg_bot.activity_status,
        ),
    )

    await message.bot.copy_message(
        chat_id=config.tg_bot.ntp_forum_id
        if "НТП" in user.Division
        else config.tg_bot.nck_forum_id,
        message_thread_id=new_topic.message_thread_id,
        from_chat_id=message.chat.id,
        message_id=state_data.get("question_message_id"),
    )  # Копирование сообщения специалиста в тему

    await message.bot.pin_chat_message(
        chat_id=config.tg_bot.ntp_forum_id
        if "НТП" in user.Division
        else config.tg_bot.nck_forum_id,
        message_id=topic_info_msg.message_id,
        disable_notification=True,
    )  # Пин информации о специалисте

    await state.clear()
    logging.info(
        f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {message.from_user.username} ({message.from_user.id}): Создан новый вопрос {new_question.token}"
    )


@user_router.callback_query(AskQuestionMenu.filter(F.found_regulation == False))
async def regulation_not_found_handler(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    questions_repo: RequestsRepo,
):
    """
    Обработчик кнопки "Не нашел" для случая, когда пользователь не смог найти регламент
    """
    state_data = await state.get_data()

    # Получаем статистику для пользователя
    employee_topics_today = await questions_repo.questions.get_questions_count_today(
        employee_fullname=user.FIO
    )
    employee_topics_month = (
        await questions_repo.questions.get_questions_count_last_month(
            employee_fullname=user.FIO
        )
    )

    # Отключаем кнопки на предыдущих шагах
    await disable_previous_buttons(callback.message, state)

    # Создаем новую тему
    new_topic = await callback.bot.create_forum_topic(
        chat_id=config.tg_bot.ntp_forum_id
        if "НТП" in user.Division
        else config.tg_bot.nck_forum_id,
        name=f"{user.Division} | {user.FIO}" if "НТП" in user.Division else user.FIO,
        icon_custom_emoji_id=dicts.topicEmojis["open"],
    )

    # Создаем новый вопрос с clever_link = "не нашел"
    new_question = await questions_repo.questions.add_question(
        group_id=int(
            config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id
        ),
        topic_id=new_topic.message_thread_id,
        employee_chat_id=callback.from_user.id,
        employee_fullname=user.FIO,
        employee_division=user.Division,
        start_time=datetime.datetime.now(),
        question_text=state_data.get("question"),
        clever_link="не нашел",  # Устанавливаем специальное значение
    )

    # Отправляем сообщение об успехе
    await callback.message.edit_text(
        """<b>✅ Успешно</b>

Вопрос передан на рассмотрение, в скором времени тебе ответят""",
        reply_markup=cancel_question_kb(token=new_question.token),
    )

    # Запускаем таймер бездействия для нового вопроса
    if new_question.status == "open":
        await start_inactivity_timer(new_question.token, callback.bot, questions_repo)

    # Формируем текст сообщения с указанием "не нашел" в регламенте
    topic_text = f"""Вопрос задает <b>{user.FIO}</b>

<b>🗃️ Регламент:</b> не нашел

<blockquote expandable><b>👔 Должность:</b> {user.Position}
<b>👑 Руководитель:</b> {user.Boss}

<b>❓ Вопросов:</b> за день {employee_topics_today} / за месяц {employee_topics_month}</blockquote>"""

    # Отправляем информацию в тему
    topic_info_msg = await callback.bot.send_message(
        chat_id=config.tg_bot.ntp_forum_id
        if "НТП" in user.Division
        else config.tg_bot.nck_forum_id,
        message_thread_id=new_topic.message_thread_id,
        text=topic_text,
        disable_web_page_preview=True,
        reply_markup=activity_status_toggle_kb(
            token=new_question.token,
            user_id=new_question.employee_chat_id,
            current_status=new_question.activity_status_enabled,
            global_status=config.tg_bot.activity_status,
        ),
    )

    # Копируем оригинальное сообщение с вопросом
    await callback.bot.copy_message(
        chat_id=config.tg_bot.ntp_forum_id
        if "НТП" in user.Division
        else config.tg_bot.nck_forum_id,
        message_thread_id=new_topic.message_thread_id,
        from_chat_id=callback.message.chat.id,
        message_id=state_data.get("question_message_id"),
    )

    # Закрепляем информационное сообщение
    await callback.bot.pin_chat_message(
        chat_id=config.tg_bot.ntp_forum_id
        if "НТП" in user.Division
        else config.tg_bot.nck_forum_id,
        message_id=topic_info_msg.message_id,
        disable_notification=True,
    )

    # Очищаем состояние
    await state.clear()

    logging.info(
        f"{'[Админ]' if state_data.get('role') or user.Role == 10 else '[Юзер]'} {callback.from_user.username} ({callback.from_user.id}): Создан новый вопрос {new_question.token} без регламента (не нашел)"
    )


@user_router.callback_query(CancelQuestion.filter(F.action == "cancel"))
async def cancel_question(
    callback: CallbackQuery,
    state: FSMContext,
    questions_repo: RequestsRepo,
    main_repo: RequestsRepo,
    user: User,
    question: Question,
):
    if (
        question
        and question.status == "open"
        and not question.topic_duty_fullname
        and not question.end_time
    ):
        await callback.bot.edit_forum_topic(
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
            message_thread_id=question.topic_id,
            icon_custom_emoji_id=dicts.topicEmojis["fired"],
        )
        await callback.bot.close_forum_topic(
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
            message_thread_id=question.topic_id,
        )
        await questions_repo.questions.delete_question(token=question.token)
        await remove_question_timer(bot=callback.bot, question=question)
        await callback.bot.send_message(
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
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


@user_router.callback_query(ActivityStatusToggle.filter())
async def toggle_activity_status(
    callback: CallbackQuery,
    callback_data: ActivityStatusToggle,
    questions_repo: RequestsRepo,
    question: Question,
):
    """Обработчик переключения статуса активности для топика"""
    try:
        if not question:
            await callback.answer("❌ Вопрос не найден", show_alert=True)
            return
        elif question.status not in ["open", "in_progress"]:
            await callback.answer("Вопрос уже закрыт")
            return

        # Определяем новое значение статуса активности
        if callback_data.action == "enable":
            new_status = True
            action_text = "включен"
        else:  # disable
            new_status = False
            action_text = "отключен"
            from tgbot.services.scheduler import stop_inactivity_timer

            stop_inactivity_timer(question.token)

        # Обновляем статус в базе данных
        await questions_repo.questions.update_question_activity_status(
            token=callback_data.token, activity_status_enabled=new_status
        )

        # Теперь запускаем таймер если включили активность
        if callback_data.action == "enable" and question.status in [
            "open",
            "in_progress",
        ]:
            await start_inactivity_timer(
                question_token=question.token,
                bot=callback.bot,
                questions_repo=questions_repo,
            )

        # Обновляем клавиатуру
        await callback.message.edit_reply_markup(
            reply_markup=activity_status_toggle_kb(
                token=callback_data.token,
                user_id=question.employee_chat_id,
                current_status=new_status,
                global_status=config.tg_bot.activity_status,
            )
        )

        # Показываем уведомление пользователю
        if new_status:
            await callback.answer(
                f"🟢 Статус активности {action_text} для данного топика"
            )
        else:
            await callback.answer(
                f"🟠 Статус активности {action_text} для данного топика"
            )

        # Отправляем уведомление в топик (автоудаление через 10 секунд)
        if new_status:
            topic_message_text = "🟢 <b>Автозакрытие включено</b>\n\nТопик будет автоматически закрыт при отсутствии активности\n\n<i>Сообщение удалится через 10 секунд</i>"
        else:
            topic_message_text = "🟠 <b>Автозакрытие отключено</b>\n\nТопик не будет закрываться автоматически\n\n<i>Сообщение удалится через 10 секунд</i>"

        topic_msg = await callback.bot.send_message(
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in question.employee_division
            else config.tg_bot.nck_forum_id,
            message_thread_id=question.topic_id,
            text=topic_message_text,
        )

        # Отправляем уведомление пользователю (автоудаление через 10 секунд)
        if new_status:
            user_message_text = "🟢 <b>Автозакрытие включено</b>\n\nВопрос включил автоматические закрытие вопроса при отсутствии активности\n\n<i>Сообщение удалится через 10 секунд</i>"
        else:
            user_message_text = "🟠 <b>Автозакрытие отключено</b>\n\nДежурный выключил автоматические закрытие вопроса при отсутствии активности\n\n<i>Сообщение удалится через 10 секунд</i>"

        user_msg = await callback.bot.send_message(
            chat_id=question.employee_chat_id,
            text=user_message_text,
        )

        # Запускаем таймеры удаления для обоих сообщений
        await run_delete_timer(
            bot=callback.bot,
            chat_id=int(
                config.tg_bot.ntp_forum_id
                if "НТП" in question.employee_division
                else config.tg_bot.nck_forum_id
            ),
            message_ids=[topic_msg.message_id],
            seconds=10,
        )

        await run_delete_timer(
            bot=callback.bot,
            chat_id=question.employee_chat_id,
            message_ids=[user_msg.message_id],
            seconds=10,
        )

        logger.info(
            f"[Активность] Пользователь {callback.from_user.username} ({callback.from_user.id}): "
            f"Статус активности {action_text} для вопроса {question.token}"
        )

    except Exception as e:
        logger.error(f"[Активность] Ошибка при переключении статуса активности: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)
