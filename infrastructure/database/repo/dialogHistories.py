import logging
from typing import Optional, List, Sequence

from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import dialogHistories
from infrastructure.database.models.dialogHistories import DialogHistories
from infrastructure.database.repo.base import BaseRepo
from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class DialogHistoriesRepo(BaseRepo):
    pass
