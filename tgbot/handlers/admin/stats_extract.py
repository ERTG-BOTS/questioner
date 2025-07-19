import logging
from datetime import datetime
from io import BytesIO

import pandas as pd
from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery

from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.admin import AdminFilter
from tgbot.keyboards.admin.main import AdminMenu
from tgbot.keyboards.admin.stats_extract import StatsExtract, extract_kb
from tgbot.services.logger import setup_logging

stats_router = Router()
stats_router.message.filter(AdminFilter())

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)

@stats_router.callback_query(AdminMenu.filter(F.menu == "stats_extract"))
async def extract_stats(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        f"""<b>📥 Выгрузка статистики</b>

Выгрузка будет содержать вопросы за указанный промежуток времени для направления <b>{config.tg_bot.division}</b>

<i>Выбери период выгрузки используя меню</i>""",
        reply_markup=extract_kb(),
    )
    await callback.answer()


@stats_router.callback_query(StatsExtract.filter(F.menu == "month"))
async def admin_extract_month(
    callback: CallbackQuery, callback_data: StatsExtract, repo: RequestsRepo
) -> None:
    logger.info("we are here")
    month = callback_data.month
    year = callback_data.year

    questions = await repo.questions.get_questions_by_month(
        month, year, division=config.tg_bot.division
    )

    data = []
    for question_row in questions:
        question = question_row[0]

        match question.QualityEmployee:
            case None:
                quality_employee = "Нет оценки"
            case True:
                quality_employee = "Хорошо"
            case False:
                quality_employee = "Плохо"
            case _:
                quality_employee = "Неизвестно"

        match question.QualityDuty:
            case None:
                quality_duty = "Нет оценки"
            case True:
                quality_duty = "Хорошо"
            case False:
                quality_duty = "Плохо"
            case _:
                quality_duty = "Неизвестно"

        match question.Status:
            case "open":
                status = "Открыт"
            case "in_progress":
                status = "В работе"
            case "closed":
                status = "Закрыт"
            case "lost":
                status = "Потерян"
            case "fired":
                status = "Удален"
            case _:
                status = "Закрыт"

        match question.AllowReturn:
            case True:
                AllowReturn = "Доступен"
            case False:
                AllowReturn = "Запрещен"
            case _:
                AllowReturn = "Неизвестно"

        data.append(
            {
                "Токен": question.Token,
                "Специалист": question.EmployeeFullname,
                "Старший": question.TopicDutyFullname,
                "Текст вопроса": question.QuestionText,
                "Время вопроса": question.StartTime,
                "Время завершения": question.EndTime,
                "Ссылка на БЗ": question.CleverLink,
                "Оценка специалиста": quality_employee,
                "Оценка дежурного": quality_duty,
                "Статус чата": status,
                "Возможность возврата": AllowReturn,
            }
        )

    if not data:
        await callback.message.answer("Не найдено данных для указанного месяца.")
        return

    # Создаем файл excel в памяти
    df = pd.DataFrame(data)
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(
            writer, sheet_name=f"{config.tg_bot.division} - {month}_{year}", index=False
        )

    excel_buffer.seek(0)

    # Создаем имя файла
    month_names = {
        1: "январь",
        2: "февраль",
        3: "март",
        4: "апрель",
        5: "май",
        6: "июнь",
        7: "июль",
        8: "август",
        9: "сентябрь",
        10: "октябрь",
        11: "ноябрь",
        12: "декабрь",
    }

    filename = (
        f"История вопросов {config.tg_bot.division} - {month_names[month]} {year}.xlsx"
    )

    # Сохраняем файл в буфер
    excel_file = BufferedInputFile(excel_buffer.getvalue(), filename=filename)

    await callback.message.answer_document(
        excel_file, caption=f"{month_names[month]} {year}"
    )

    await callback.answer()


@stats_router.callback_query(StatsExtract.filter(F.menu == "bulk"))
async def admin_extract_bulk(
    callback: CallbackQuery, callback_data: StatsExtract, repo: RequestsRepo
) -> None:
    months_count = callback_data.months
    current_date = datetime.now()

    all_data = []

    # Collect data for the specified number of months
    for i in range(months_count):
        year = current_date.year
        month = current_date.month - i
        if month <= 0:
            month += 12
            year -= 1

        questions = await repo.questions.get_questions_by_month(
            month, year, division=config.tg_bot.division
        )

        for question_row in questions:
            question = question_row[0]

            match question.QualityEmployee:
                case None:
                    quality_employee = "Нет оценки"
                case True:
                    quality_employee = "Хорошо"
                case False:
                    quality_employee = "Плохо"
                case _:
                    quality_employee = "Неизвестно"

            match question.QualityDuty:
                case None:
                    quality_duty = "Нет оценки"
                case True:
                    quality_duty = "Хорошо"
                case False:
                    quality_duty = "Плохо"
                case _:
                    quality_duty = "Неизвестно"

            match question.Status:
                case "open":
                    status = "Открыт"
                case "in_progress":
                    status = "В работе"
                case "closed":
                    status = "Закрыт"
                case "lost":
                    status = "Потерян"
                case "fired":
                    status = "Удален"
                case _:
                    status = "Закрыт"

            match question.AllowReturn:
                case True:
                    AllowReturn = "Доступен"
                case False:
                    AllowReturn = "Запрещен"
                case _:
                    AllowReturn = "Неизвестно"

            all_data.append(
                {
                    "Токен": question.Token,
                    "Специалист": question.EmployeeFullname,
                    "Старший": question.TopicDutyFullname,
                    "Текст вопроса": question.QuestionText,
                    "Время вопроса": question.StartTime,
                    "Время завершения": question.EndTime,
                    "Ссылка на БЗ": question.CleverLink,
                    "Оценка специалиста": quality_employee,
                    "Оценка дежурного": quality_duty,
                    "Статус чата": status,
                    "Возможность возврата": AllowReturn,
                }
            )

    if not all_data:
        await callback.message.answer(
            f"Не найдено данных за последние {months_count} месяцев."
        )
        return

    # Создаем файл excel в памяти
    df = pd.DataFrame(all_data)

    # Sort by date
    df = df.sort_values("Время вопроса", ascending=False)

    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            sheet_name=f"{config.tg_bot.division} - {months_count} месяцев",
            index=False,
        )

    excel_buffer.seek(0)

    # Создаем имя файла
    filename = f"История вопросов {config.tg_bot.division} - последние {months_count} месяцев.xlsx"

    # Сохраняем файл в буфер
    excel_file = BufferedInputFile(excel_buffer.getvalue(), filename=filename)

    await callback.message.answer_document(
        excel_file, caption=f"Последние {months_count} месяцев"
    )

    await callback.answer()