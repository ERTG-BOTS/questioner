from datetime import datetime

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.keyboards.admin.main import AdminMenu


class MonthStatsExtract(CallbackData, prefix="month_stats"):
    menu: str
    month: int
    year: int


# Выбор дат для выгрузки статистики
def extract_kb() -> InlineKeyboardMarkup:
    current_date = datetime.now()

    # Get month names in Russian
    month_names = {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Июль",
        8: "Август",
        9: "Сентябрь",
        10: "Октябрь",
        11: "Ноябрь",
        12: "Декабрь",
    }

    buttons = []

    # Generate last 6 months in pairs (2 columns)
    for i in range(0, 2, 2):
        row = []

        # First month in the row
        year1 = current_date.year
        month1 = current_date.month - i
        if month1 <= 0:
            month1 += 12
            year1 -= 1

        month1_name = month_names[month1]
        row.append(
            InlineKeyboardButton(
                text=f"📅 {month1_name} {year1}",
                callback_data=MonthStatsExtract(
                    menu="month", month=month1, year=year1
                ).pack(),
            )
        )

        # Second month in the row (if exists)
        if i + 1 < 6:
            year2 = current_date.year
            month2 = current_date.month - (i + 1)
            if month2 <= 0:
                month2 += 12
                year2 -= 1

            month2_name = month_names[month2]
            row.append(
                InlineKeyboardButton(
                    text=f"📅 {month2_name} {year2}",
                    callback_data=MonthStatsExtract(
                        menu="month", month=month2, year=year2
                    ).pack(),
                )
            )

        buttons.append(row)

    # Add back button
    buttons.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад", callback_data=AdminMenu(menu="reset").pack()
            ),
        ]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
