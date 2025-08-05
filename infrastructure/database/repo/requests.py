from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.pairs import MessagesPairsRepo
from infrastructure.database.repo.questions import QuestionsRepo
from infrastructure.database.repo.settings import SettingsRepo
from infrastructure.database.repo.users import UserRepo


@dataclass
class RequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession

    @property
    def users(self) -> UserRepo:
        """
        The User repository sessions are required to manage user operations.
        """
        return UserRepo(self.session)

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
