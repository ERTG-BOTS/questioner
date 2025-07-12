from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.admin.main import AdminMenu


class MainMenu(CallbackData, prefix='menu'):
    menu: str


# Основная клавиатура для команды /start
def user_kb(role: int, is_role_changed: bool = False) -> InlineKeyboardMarkup:
    buttons = []

    common_buttons = [
        [InlineKeyboardButton(text="🏅 Профиль", callback_data=MainMenu(menu="level").pack())],
        [
            InlineKeyboardButton(text="🎯 Ачивки", callback_data=MainMenu(menu="achievements").pack()),
            InlineKeyboardButton(text="👏 Награды", callback_data=MainMenu(menu="awards").pack()),
        ],
        [
            InlineKeyboardButton(text="❓️ FAQ", callback_data=MainMenu(menu="faq").pack()),
            InlineKeyboardButton(text="🙋‍♂️ Помогите", url="https://t.me/+n43FvDM6Z1I3Yzg6"),
        ]
    ]

    # Логика для определенных ролей
    if role in {2, 3, 5, 6}:
        # Кнопка активации наград для этих ролей
        buttons.append([
            InlineKeyboardButton(text="⭐ Награды для активации",
                                 callback_data=MainMenu(menu="awards_activation").pack()),
        ])

        # Добавляем кнопки обычного пользователя для старшего
        if role == 3:
            buttons.extend(common_buttons)
    elif role == 1:
        buttons.extend(common_buttons)

    # Добавляем кнопку сброса если роль измененная
    if is_role_changed:
        buttons.append([
            InlineKeyboardButton(text="♻️ Сбросить роль", callback_data=AdminMenu(menu="reset").pack()),
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Клавиатура с кнопкой возврата в главное меню
def back_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data=MainMenu(menu="main").pack()),
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard
