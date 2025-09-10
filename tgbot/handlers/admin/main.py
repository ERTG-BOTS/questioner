import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.admin import AdminFilter
from tgbot.filters.topic import IsTopicMessage
from tgbot.handlers.user.main import main_cb
from tgbot.keyboards.admin.main import (
    AdminMenu,
    ChangeRole,
    SelectDivision,
    admin_kb,
    division_selection_kb,
)
from tgbot.keyboards.user.main import user_kb
from tgbot.misc.dicts import role_names
from tgbot.misc.helpers import short_name
from tgbot.services.logger import setup_logging

admin_router = Router()
admin_router.message.filter(AdminFilter())

setup_logging()
logger = logging.getLogger(__name__)


@admin_router.message(CommandStart(), ~IsTopicMessage())
async def admin_start(
    message: Message, state: FSMContext, user: User, questions_repo: RequestsRepo
) -> None:
    employee_topics_today = await questions_repo.questions.get_questions_count_today(
        employee_fullname=user.FIO
    )
    employee_topics_month = (
        await questions_repo.questions.get_questions_count_last_month(
            employee_fullname=user.FIO
        )
    )

    state_data = await state.get_data()

    if "role" in state_data:
        # Определяем текущую временную роль
        temp_division = state_data.get("temp_division", "")
        role_text = f"Специалист ({temp_division})" if temp_division else "Специалист"

        logging.info(
            f"[Админ] {message.from_user.username} ({message.from_user.id}): Открыто меню пользователя"
        )
        await message.answer(
            f"""👋 Привет, <b>{short_name(user.FIO)}</b>!

<b>🎭 Твоя временная роль:</b> {role_text}

<b>❓ Ты задал вопросов:</b>
- За день {employee_topics_today}
- За месяц {employee_topics_month}

Используй меню, чтобы выбрать действие""",
            reply_markup=user_kb(
                is_role_changed=True if state_data.get("role") else False
            ),
        )
        return

    await message.answer(
        f"""👋 Привет, <b>{short_name(user.FIO)}</b>!

<b>🎭 Твоя роль:</b> {role_names[user.Role]}

<i>Используй меню для управления ботом</i>""",
        reply_markup=admin_kb(),
    )

    logging.info(
        f"[Админ] {message.from_user.username} ({message.from_user.id}): Открыто админ-меню"
    )


@admin_router.callback_query(ChangeRole.filter())
async def change_role(
    callback: CallbackQuery,
    callback_data: ChangeRole,
    state: FSMContext,
    questions_repo: RequestsRepo,
    user: User,
) -> None:
    match callback_data.role:
        case "spec":
            await state.update_data(role=1)  # Специалист
            logging.info(
                f"[Админ] {callback.from_user.username} ({callback.from_user.id}): Роль изменена с {user.Role} на 1"
            )

    await main_cb(
        callback=callback, state=state, questions_repo=questions_repo, user=user
    )
    await callback.answer()


@admin_router.callback_query(AdminMenu.filter(F.menu == "reset"))
async def reset_role_cb(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    """
    Сброс кастомной роли через клавиатуру
    """
    state_data = await state.get_data()
    await state.clear()

    await callback.message.edit_text(
        f"""Привет, <b>{short_name(user.FIO)}</b>!

<b>🎭 Твоя роль:</b> {role_names[user.Role]}

<i>Используй меню для управления ботом</i>""",
        reply_markup=admin_kb(),
    )

    logging.info(
        f"[Админ] Пользователь {callback.from_user.username} ({callback.from_user.id}): Роль изменена с {state_data.get('role')} на {user.Role} кнопкой"
    )
    await callback.answer()


@admin_router.callback_query(AdminMenu.filter(F.menu == "change_role"))
async def show_division_selection(
    callback: CallbackQuery,
) -> None:
    """
    Показывает меню выбора направления для смены роли
    """
    await callback.message.edit_text(
        """<b>🎭 Изменение роли</b>

Выбери новую роль из списка:
- <b>НЦК</b> - Специалист НЦК
- <b>НЦК ОР</b> - Специалист НЦК Общего Ряда (стажёры)
- <b>НТП</b> - Специалист НТП""",
        reply_markup=division_selection_kb(),
    )

    logging.info(
        f"[Админ] {callback.from_user.username} ({callback.from_user.id}): Открыто меню выбора направления"
    )
    await callback.answer()


@admin_router.callback_query(SelectDivision.filter())
async def change_role_to_division(
    callback: CallbackQuery,
    callback_data: SelectDivision,
    state: FSMContext,
    questions_repo: RequestsRepo,
    user: User,
) -> None:
    """
    Изменяет роль админа на специалиста выбранного направления
    """
    division = callback_data.division

    # Устанавливаем роль специалиста (1) и сохраняем выбранное направление
    await state.update_data(
        role=1,  # Специалист
        temp_division=division,  # Сохраняем выбранное направление
    )

    logging.info(
        f"[Админ] {callback.from_user.username} ({callback.from_user.id}): "
        f"Роль изменена с {user.Role} на специалиста {division}"
    )

    await main_cb(
        callback=callback, state=state, questions_repo=questions_repo, user=user
    )
    await callback.answer()


@admin_router.message(Command("reset"))
async def reset_role_cmd(message: Message, state: FSMContext, user: User) -> None:
    """
    Сброс кастомной роли через команду
    """
    state_data = await state.get_data()
    await state.clear()

    await message.answer(
        f"""👋 Привет, <b>{short_name(user.FIO)}</b>!

<b>🎭 Твоя роль:</b> {role_names[user.Role]}

<i>Используй меню для управления ботом</i>""",
        reply_markup=admin_kb(),
    )

    logging.info(
        f"[Админ] {message.from_user.username} ({message.from_user.id}): Роль изменена с {state_data.get('role')} на {user.Role} командой"
    )


@admin_router.callback_query(AdminMenu.filter(F.menu == "main"))
async def back_to_main_menu(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    questions_repo: RequestsRepo,
) -> None:
    """
    Возврат в главное админ-меню
    """
    await admin_start(callback.message, state, user, questions_repo)
    await callback.answer()
