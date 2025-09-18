from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repo.STP.employee import EmployeeRepo


@dataclass
class MainRequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession

    @property
    def employee(self) -> EmployeeRepo:
        """
        The Employee repository sessions are required to manage user operations.
        """
        return EmployeeRepo(self.session)
