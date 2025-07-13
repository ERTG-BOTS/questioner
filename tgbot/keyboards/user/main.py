from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.keyboards.admin.main import AdminMenu


class MainMenu(CallbackData, prefix='menu'):
    menu: str


class DialogQualitySpecialist(CallbackData, prefix='d_quality_spec'):
    answer: bool
    token: str

class DialogQualityDuty(CallbackData, prefix='d_quality_duty'):
    answer: bool
    token: str


# Основная клавиатура для команды /start
def user_kb(is_role_changed: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🤔 Задать вопрос", callback_data=MainMenu(menu="ask").pack()),
            InlineKeyboardButton(text="🔄 Вернуть вопрос", callback_data=MainMenu(menu="ask").pack()),
        ]
    ]

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


# Клавиатура с отменой вопроса и возвратом в главное меню
def cancel_question_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🙅‍♂️ Отменить вопрос", callback_data=MainMenu(menu="main").pack()),
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


# Клавиатура с отменой вопроса и возвратом в главное меню
def finish_question_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅️ Завершить диалог", callback_data=MainMenu(menu="main").pack()),
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


# Клавиатура оценки диалога
def dialog_quality_kb(token: str, role: str = "employee") -> InlineKeyboardMarkup:
    if role == "employee":
        buttons = [
            [
                InlineKeyboardButton(text="👍 Да", callback_data=DialogQualitySpecialist(answer=True, token=token).pack()),
                InlineKeyboardButton(text="👎 Нет", callback_data=DialogQualitySpecialist(answer=False, token=token).pack()),
            ]
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(text="👎 Да",
                                     callback_data=DialogQualityDuty(answer=False, token=token).pack()),
                InlineKeyboardButton(text="👍 Нет",
                                     callback_data=DialogQualityDuty(answer=True, token=token).pack()),
            ]
        ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard