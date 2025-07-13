import datetime
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from infrastructure.database.models import User, Dialog
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.active_question import ActiveQuestion
from tgbot.keyboards.user.main import user_kb, MainMenu, back_kb, cancel_question_kb, DialogQualitySpecialist
from tgbot.misc import dicts
from tgbot.misc.states import Question
from tgbot.services.logger import setup_logging

user_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)

@user_router.message(CommandStart())
async def main_cmd(message: Message, state: FSMContext, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        user: User = await repo.users.get_user(user_id=message.from_user.id)

    division = "НТП" if config.tg_bot.division == "ntp" else "НЦК"
    state_data = await state.get_data()

    if user:
        await message.answer(f"""👋 Привет, <b>{user.FIO}</b>!

Я - бот-вопросник {division}

<i>Используй меню для управление ботом</i>""",
                             reply_markup=user_kb(is_role_changed=True if state_data.get("role") else False))
    else:
        await message.answer(f"""Привет, <b>@{message.from_user.username}</b>!
        
Не нашел тебя в списке зарегистрированных пользователей

Регистрация происходит через бота Графиков
Если возникли сложности с регистраций обратись к МиП

Если ты зарегистрировался недавно, напиши <b>/start</b>""")


@user_router.callback_query(MainMenu.filter(F.menu == "main"))
async def main_cb(callback: CallbackQuery, stp_db, state: FSMContext):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        user: User = await repo.users.get_user(user_id=callback.from_user.id)

    division = "НТП" if config.tg_bot.division == "ntp" else "НЦК"
    state_data = await state.get_data()

    await callback.message.edit_text(f"""Привет, <b>{user.FIO}</b>!

Я - бот-вопросник {division}

Используй меню, чтобы выбрать действие""",
                                     reply_markup=user_kb(is_role_changed=True if state_data.get("role") else False))


@user_router.callback_query(MainMenu.filter(F.menu == "ask"))
async def ask_question(callback: CallbackQuery, state: FSMContext, stp_db):
    msg = await callback.message.edit_text(f"""<b>🤔 Суть вопроса</b>

Отправь вопрос и вложения одним сообщением""", reply_markup=back_kb())

    # Initialize list to store message IDs with buttons
    await state.update_data(messages_with_buttons=[msg.message_id])
    await state.set_state(Question.question)


@user_router.message(Question.question)
async def question_text(message: Message, state: FSMContext):
    await state.update_data(question=message.text)
    await state.update_data(question_message_id=message.message_id)

    # Disable buttons from previous step
    await disable_previous_buttons(message, state)

    # Store the message ID of the current step to disable buttons later
    response_msg = await message.answer(f"""<b>🗃️ Регламент</b>

Прикрепи ссылку на регламент из клевера, по которому у тебя вопрос""", reply_markup=back_kb())

    # Add current message to the list
    state_data = await state.get_data()
    messages_with_buttons = state_data.get("messages_with_buttons", [])
    messages_with_buttons.append(response_msg.message_id)
    await state.update_data(messages_with_buttons=messages_with_buttons)

    await state.set_state(Question.clever_link)


@user_router.message(Question.clever_link)
async def clever_link_handler(message: Message, state: FSMContext, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        user: User = await repo.users.get_user(user_id=message.from_user.id)

    clever_link = message.text
    state_data = await state.get_data()

    if not "clever.ertelecom.ru/content/space/" in message.text and user.Role != 10:
        await message.answer(f"""<b>🗃️ Регламент</b>

Сообщение <b>не содержит ссылку на клевер</b> 🥺

Отправь ссылку на регламент из клевера, по которому у тебя вопрос""", reply_markup=back_kb())
        return

    # Disable all previous buttons
    await disable_previous_buttons(message, state)

    await message.answer(f"""<b>✅ Успешно</b>

Вопрос передан на рассмотрение, в скором времени тебе ответят""", reply_markup=cancel_question_kb())


    new_topic = await message.bot.create_forum_topic(chat_id=config.tg_bot.forum_id, name=user.FIO,
                                                     icon_custom_emoji_id=dicts.topicEmojis["open"])  # Создание топика
    await message.bot.close_forum_topic(chat_id=config.tg_bot.forum_id,
                                        message_thread_id=new_topic.message_thread_id)  # Закрытие топика

    await repo.dialogs.add_dialog(employee_chat_id=message.chat.id,
                                  employee_fullname=user.FIO,
                                  topic_id=new_topic.message_thread_id,
                                  start_time=datetime.datetime.now(),
                                  question=state_data.get("question"),
                                  clever_link=clever_link)  # Добавление диалога в БД

    employee_topics_today = await repo.dialogs.get_dialogs_count_today(employee_fullname=user.FIO)
    employee_topics_month = await repo.dialogs.get_dialogs_count_last_month(employee_fullname=user.FIO)

    topic_info_msg = await message.bot.send_message(chat_id=config.tg_bot.forum_id,
                                                    message_thread_id=new_topic.message_thread_id,
                                                    text=f"""Вопрос задает <b>{user.FIO}</b> {'(<a href="https://t.me/' + user.Username + '">лс</a>)' if user.Username != "Не указан" else ""}

<b>🗃️ Регламент:</b> <a href='{clever_link}'>тык</a>

<blockquote expandable><b>👔 Должность:</b> {user.Position}
<b>👑 РГ:</b> {user.Boss}

<b>❓ Вопросов:</b> за день {employee_topics_today} / за месяц {employee_topics_month}</blockquote>""", disable_web_page_preview=True)

    await message.bot.pin_chat_message(chat_id=config.tg_bot.forum_id,
                                       message_id=topic_info_msg.message_id, disable_notification=True)  # Пин информации о специалисте

    await message.bot.copy_message(chat_id=config.tg_bot.forum_id, message_thread_id=new_topic.message_thread_id,
                                   from_chat_id=message.chat.id, message_id=state_data.get(
            "question_message_id"))  # Копирование сообщения специалиста в топик

    await message.bot.reopen_forum_topic(chat_id=config.tg_bot.forum_id,
                                         message_thread_id=new_topic.message_thread_id)  # Переоткрытие топика

    await state.clear()


@user_router.callback_query(DialogQualitySpecialist.filter())
async def dialog_quality_employee(callback: CallbackQuery, callback_data: DialogQualitySpecialist, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        duty: User = await repo.users.get_user(user_id=callback.from_user.id)

    await repo.dialogs.update_dialog_quality(token=callback_data.token, quality=callback_data.answer, is_duty=False)
    await callback.answer("Оценка успешно выставлена ❤️")
    if callback_data.answer:
            await callback.message.edit_text(f"""<b>🔒 Диалог закрыт</b>

Старший <b>{duty.FIO}</b> закрыл диалог

Ты поставил оценку:
👍 Старший <b>помог решить твой вопрос</b>""")
    else:
        await callback.message.edit_text(f"""<b>🔒 Диалог закрыт</b>

Старший <b>{duty.FIO}</b> закрыл диалог

Ты поставил оценку:
👎 Старший <b>не помог решить твой вопрос</b>""")

async def disable_previous_buttons(message: Message, state: FSMContext):
    """Helper function to disable buttons from previous steps"""
    state_data = await state.get_data()
    messages_with_buttons = state_data.get("messages_with_buttons", [])

    for msg_id in messages_with_buttons:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=msg_id,
                reply_markup=None
            )
        except Exception as e:
            # Handle case where message might be deleted or not editable
            print(f"Could not disable buttons for message {msg_id}: {e}")

    # Clear the list after disabling buttons
    await state.update_data(messages_with_buttons=[])


@user_router.message(ActiveQuestion())
async def active_question(message: Message, stp_db, active_dialog_token: str = None):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        dialog: Dialog = await repo.dialogs.get_dialog(token=active_dialog_token)

    await message.bot.copy_message(from_chat_id=message.chat.id, message_id=message.message_id, chat_id=config.tg_bot.forum_id, message_thread_id=dialog.TopicId)
