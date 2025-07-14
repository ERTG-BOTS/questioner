"""Import all routers and add them to routers_list."""
from .admin.main import admin_router
from tgbot.handlers.user.main import user_router
from .group.main import topic_router
from .user.dialog import user_dialog_router
from .user.question_return import user_return_question_router

routers_list = [
    admin_router,
    topic_router,
    user_router,
    user_dialog_router,
    user_return_question_router
]

__all__ = [
    "routers_list",
]
