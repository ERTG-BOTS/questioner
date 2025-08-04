import logging

import aiohttp
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from tgbot.config import load_config
from tgbot.services.logger import setup_logging

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


async def is_employee_intern(username: str, division: str) -> bool:
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

        creds = service_account.Credentials.from_service_account_file(
            "./service_account.json", scopes=scopes
        )
        creds.refresh(Request())
        access_token = creds.token

        range_query = f"{config.gsheets.ntp_trainee_sheet_name if 'НТП' in division else config.gsheets.nck_trainee_sheet_name}!A:A"
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{config.gsheets.ntp_trainee_spreadsheet_id if 'НТП' in division else config.gsheets.nck_trainee_spreadsheet_id}/values/{range_query}"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(
                        "[Проверка ОР] Не удалось открыть таблицу:", await resp.text()
                    )
                    return False
                data = await resp.json()

        values = data.get("values", [])
        for row in values:
            if row and row[0].strip() == f"@{username}":
                return True

        return False

    except Exception as e:
        print(f"Error: {e}")
        return False


async def get_target_forum(
    username: str,
    division: str,
    temp_division: str = None,
) -> int | str:
    """
    Определяет целевой форум для создания вопроса

    :param username: Username пользователя
    :param division: Направление пользователя из БД
    :param temp_division: Временное направление из состояния (для админов)
    :return: ID целевого форума
    """
    # Если есть временное направление (админ сменил роль), используем его
    if temp_division:
        # Админ явно выбрал направление - не проверяем статус стажёра
        if temp_division == "НЦК":
            target_forum_id = config.forum.nck_main_forum_id
            logger.info(f"[Админ роль] Пользователь {username} маскируется под НЦК")

        elif temp_division == "НЦК ОР":
            target_forum_id = config.forum.nck_trainee_forum_id
            logger.info(f"[Админ роль] Пользователь {username} маскируется под НЦК ОР")

        elif temp_division == "НТП":
            target_forum_id = config.forum.ntp_main_forum_id
            logger.info(f"[Админ роль] Пользователь {username} маскируется под НТП")

        elif temp_division == "НТП ОР":
            target_forum_id = config.forum.ntp_trainee_forum_id
            logger.info(f"[Админ роль] Пользователь {username} маскируется под НТП ОР")

        else:
            # Fallback если что-то пошло не так
            target_forum_id = config.forum.nck_main_forum_id
            logger.warning(
                f"[Админ роль] Неизвестное временное направление: {temp_division}"
            )

        return target_forum_id

    # Обычная логика для пользователей (не админов с временной ролью)
    if division == "НЦК":
        try:
            # Проверяем, является ли пользователь стажёром
            is_intern = await is_employee_intern(username=username, division=division)

            if is_intern:
                # Если стажёр - используем специальный форум для стажёров
                target_forum_id = config.forum.nck_trainee_forum_id
                logger.info(f"[Проверка ОР] [НЦК] Определен стажер: {username}")
            else:
                # Если не стажёр - используем обычный НЦК форум
                target_forum_id = config.forum.nck_main_forum_id

        except Exception as e:
            # В случае ошибки при проверке стажёра, отправляем в основной НЦК форум
            logging.error(
                f"Ошибка при проверке стажёра для пользователя {username}: {e}"
            )
            target_forum_id = config.forum.nck_main_forum_id
    else:
        try:
            # Проверяем, является ли пользователь стажёром
            is_intern = await is_employee_intern(username=username, division=division)

            if is_intern:
                # Если стажёр - используем специальный форум для стажёров
                target_forum_id = config.forum.ntp_trainee_forum_id
                logger.info(f"[Проверка ОР] [НТП] Определен стажер: {username}")
            else:
                # Если не стажёр - используем обычный НТП форум
                target_forum_id = config.forum.ntp_main_forum_id

        except Exception as e:
            # В случае ошибки при проверке стажёра, отправляем в основной НТП форум
            logging.error(
                f"Ошибка при проверке стажёра для пользователя {username}: {e}"
            )
            target_forum_id = config.forum.ntp_main_forum_id

    return target_forum_id
