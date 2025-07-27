from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class RemovedUser(CallbackData, prefix="removed_user"):
    action: str
    user_id: int | str
    role: int = None


def on_user_join_kb(user_link: str = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для использования после добавления в группу

    :param user_link: Ссылка на пользователя в Telegram
    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="💬 Написать в ЛС",
                url=user_link,
            ),
        ]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return keyboard


def on_user_leave_kb(
    user_id: int | str,
    unban: bool = True,
    change_role: bool = False,
    new_role: int = None,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для использования после удаления из группы

    :param user_link: Ссылка на пользователя в Telegram
    :return: Объект встроенной клавиатуры для возврата главного меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="💬 Написать в ЛС",
                url=f"tg://user?id={user_id}",
            ),
        ]
    ]

    if unban:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🗝️ Разблокировать",
                    callback_data=RemovedUser(action="unban", user_id=user_id).pack(),
                )
            ]
        )

    if change_role:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Это РГ",
                    callback_data=RemovedUser(
                        action="change_role", user_id=user_id, role=2
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="Это старший",
                    callback_data=RemovedUser(
                        action="change_role", user_id=user_id, role=3
                    ).pack(),
                ),
            ],
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return keyboard
