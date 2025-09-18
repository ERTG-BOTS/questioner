from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.questions.pairs import MessagesPairsRepo
from infrastructure.database.repo.questions.questions import QuestionsRepo
from infrastructure.database.repo.questions.settings import SettingsRepo


@dataclass
class QuestionsRequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession

    @property
    def questions(self) -> QuestionsRepo:
        """
        The QuestionsRepo repository sessions are required to manage question questions operations.
        """
        return QuestionsRepo(self.session)

    @property
    def messages_pairs(self) -> MessagesPairsRepo:
        """
        The MessageConnectionRepo repository sessions are required to manage message connections.
        """
        return MessagesPairsRepo(self.session)

    @property
    def settings(self) -> SettingsRepo:
        """
        The SettingsRepo repository sessions are required to manage bot settings.
        """
        return SettingsRepo(self.session)
