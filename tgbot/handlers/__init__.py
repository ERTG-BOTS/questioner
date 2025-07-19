"""Import all routers and add them to routers_list."""

from tgbot.handlers.user.main import user_router

from .admin.main import admin_router
from .admin.stats_extract import stats_router
from .group.cmds import topic_cmds_router
from .group.main import topic_router
from .user.active_question import user_q_router
from .user.return_question import employee_return_q

routers_list = [
    admin_router,
    stats_router,
    topic_cmds_router,
    topic_router,
    user_router,
    user_q_router,
    employee_return_q,
]

__all__ = [
    "routers_list",
]
