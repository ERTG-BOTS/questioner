from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.questions import QuestionsRepo
from infrastructure.database.repo.users import UserRepo
from infrastructure.database.repo.connections import QuestionsConnectionsRepo


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
        The QuestionsRepo repository sessions are required to manage dialog questions operations.
        """
        return QuestionsRepo(self.session)

    @property
    def questions_connections(self) -> QuestionsConnectionsRepo:
        """
        The MessageConnectionRepo repository sessions are required to manage message connections.
        """
        return QuestionsConnectionsRepo(self.session)
