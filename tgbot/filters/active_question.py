import logging

from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy import Sequence

from infrastructure.database.models import Dialog
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class ActiveQuestion(BaseFilter):

    async def __call__(self, obj: Message, stp_db, **kwargs) -> dict[str, str] | bool:
        async with stp_db() as session:
            repo = RequestsRepo(session)
            current_dialogs: Sequence[Dialog] = await repo.dialogs.get_active_dialogs()

            for dialog in current_dialogs:
                if dialog.EmployeeChatId == obj.from_user.id:
                    active_dialog_token = dialog.Token
                    return {"active_dialog_token": active_dialog_token}

            return False