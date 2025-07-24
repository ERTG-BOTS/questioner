import logging

from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy import Sequence

from infrastructure.database.models import Question
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class ActiveQuestion(BaseFilter):
    async def __call__(
        self, obj: Message, questions_repo: RequestsRepo, **kwargs
    ) -> bool:
        """
        asd
        :param obj: Объект обрабатываемого фильтром сообщения
        :param questions_repo: БД репозиторий вопросов
        :param kwargs: Дополнительные аргументы
        :return: Статус, есть ли у пользователя активный вопрос
        """
        active_questions: Sequence[
            Question
        ] = await questions_repo.questions.get_active_questions()

        for question in active_questions:
            if question.employee_chat_id == obj.from_user.id:
                return True

        return False


class ActiveQuestionWithCommand(BaseFilter):
    def __init__(self, command: str = None):
        self.command = command

    async def __call__(
        self, obj: Message, questions_repo: RequestsRepo, **kwargs
    ) -> None | bool | dict[str, str]:
        if self.command:
            if not obj.text or not obj.text.startswith(f"/{self.command}"):
                return False

            current_questions: Sequence[
                Question
            ] = await questions_repo.questions.get_active_questions()

            for question in current_questions:
                if question.employee_chat_id == obj.from_user.id:
                    return True

            return False
        return None
