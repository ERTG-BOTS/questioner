"""Import all routers and add them to routers_list."""

from tgbot.handlers.user.main import user_router

from .admin.main import admin_router
from .group.main import topic_router
from .user.active_question import user_dialog_router
from .user.return_question import employee_return_q

routers_list = [
    admin_router,
    topic_router,
    user_router,
    user_dialog_router,
    employee_return_q,
]

__all__ = [
    "routers_list",
]
