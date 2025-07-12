from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class AdminMenu(CallbackData, prefix='admin_menu'):
    menu: str


class ChangeRole(CallbackData, prefix='role'):
    role: str


# Основная клавиатура для команды /start
def admin_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="👗 Стать МИП", callback_data=ChangeRole(role="mip").pack()),
            InlineKeyboardButton(text="👮 Стать ГОК", callback_data=ChangeRole(role="gok").pack()),
        ],
        [
            InlineKeyboardButton(text="👴🏻 Стать старшим", callback_data=ChangeRole(role="duty").pack()),
            InlineKeyboardButton(text="👶🏻 Стать спецом", callback_data=ChangeRole(role="spec").pack()),
        ],
        [
            InlineKeyboardButton(text="🔎 Поиск сотрудника", callback_data=AdminMenu(menu="search").pack()),
        ]]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard
