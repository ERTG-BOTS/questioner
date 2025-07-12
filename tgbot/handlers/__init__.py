"""Import all routers and add them to routers_list."""
from .admin.main import admin_router
from tgbot.handlers.user.main import user_router

routers_list = [
    admin_router,
    user_router,
]

__all__ = [
    "routers_list",
]
