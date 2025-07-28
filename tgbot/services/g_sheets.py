import logging

import aiohttp
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from tgbot.config import load_config
from tgbot.services.logger import setup_logging

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


async def is_employee_intern(
    username: str,
) -> bool:
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

        creds = service_account.Credentials.from_service_account_file(
            "./service_account.json", scopes=scopes
        )
        creds.refresh(Request())
        access_token = creds.token

        range_query = f"{config.tg_bot.interns_sheet_name}!A:A"
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{config.tg_bot.interns_spreadsheet_id}/values/{range_query}"
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
) -> int | str:
    if division == "НЦК":
        try:
            # Проверяем, является ли пользователь стажёром
            is_intern = await is_employee_intern(username=username)

            if is_intern:
                # Если стажёр - используем специальный форум для стажёров
                target_forum_id = config.tg_bot.nck_or_forum_id
                logger.info(f"[Проверка ОР] Определен стажер: {username}")
            else:
                # Если не стажёр - используем обычный НЦК форум
                target_forum_id = config.tg_bot.nck_forum_id

        except Exception as e:
            # В случае ошибки при проверке стажёра, отправляем в основной НЦК форум
            logging.error(
                f"Ошибка при проверке стажёра для пользователя {username}: {e}"
            )
            target_forum_id = config.tg_bot.nck_forum_id
    else:
        # Для НТП используем соответствующий форум
        target_forum_id = config.tg_bot.ntp_forum_id

    return target_forum_id
