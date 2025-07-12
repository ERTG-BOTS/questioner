from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from infrastructure.database.models import Users
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.keyboards.user.main import user_kb, MainMenu, back_kb

user_router = Router()

config = load_config(".env")


@user_router.message(CommandStart())
async def main_cmd(message: Message, state: FSMContext, stp_db):
    async with stp_db() as session:
        repo = RequestsRepo(session)
        user: Users = await repo.users.get_user(user_id=message.from_user.id)

    division = "НТП" if config.tg_bot.division == "ntp" else "НЦК"
    state_data = await state.get_data()

    if user:
        await message.answer(f"""👋 Привет, <b>{user.FIO}</b>!

Я - бот-вопросник {division}

<i>Используй меню для управление ботом</i>""", reply_markup=user_kb(role=int(state_data.get("role")) if state_data.get("role") else user.Role, is_role_changed=True if state_data.get("role") else False))
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

Используй меню, чтобы выбрать действие""", reply_markup=user_kb(role=int(state_data.get("role")) if state_data.get("role") else user.Role, is_role_changed=True if state_data.get("role") else False))
