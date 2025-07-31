import logging

from aiogram import F, Router
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import CallbackQuery, ChatMemberUpdated

from infrastructure.database.models import User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.keyboards.group.events import RemovedUser, on_user_leave_kb
from tgbot.misc.dicts import group_admin_titles, role_names
from tgbot.services.logger import setup_logging

group_events_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@group_events_router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated, main_repo: RequestsRepo):
    user: User = await main_repo.users.get_user(event.from_user.id)

    if user is None:
        return

    if user not in [2, 3, 10]:
        return

    await event.answer(
        text=f"""<b>Новый пользователь</b>

👋 {user.FIO} присоединился 

<b>👔 Должность:</b>{user.Position}
<b>👑 Руководитель:</b>{user.Boss}

<i><b>Роль:</b> {role_names[user.Role]}</i>""",
    )

    # TODO удалить промоут при накате общих прав на приглашения в группу
    await event.bot.promote_chat_member(
        chat_id=event.from_user.id, user_id=event.from_user.id, can_invite_users=True
    )

    await event.bot.set_chat_administrator_custom_title(
        chat_id=event.chat.id,
        user_id=event.from_user.id,
        custom_title=group_admin_titles[user.Role],
    )


@group_events_router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_leave(event: ChatMemberUpdated, user: User):
    left_user_id = event.new_chat_member.user.id
    action_user_id = event.from_user.id

    if left_user_id == action_user_id:
        await event.answer(
            text=f"""<b>🚪 Выход</b>

Пользователь <code>{user.FIO}</code> вышел из группы""",
            reply_markup=on_user_leave_kb(user_id=left_user_id),
        )
    else:
        # User was kicked by someone else
        kicker_user = await event.bot.get_chat_member(event.chat.id, action_user_id)
        await event.answer(
            text=f"""<b>🙅‍♂️ Исключение</b>

Пользователь <code>{user.FIO}</code> был исключен администратором <code>{kicker_user.user.first_name}</code>""",
            reply_markup=on_user_leave_kb(user_id=left_user_id),
        )


@group_events_router.callback_query(RemovedUser.filter(F.action == "unban"))
async def unban_removed_user(
    callback: CallbackQuery,
    callback_data: RemovedUser,
    user: User,
    main_repo: RequestsRepo,
):
    removed_user: User = await main_repo.users.get_user(callback_data.user_id)
    if user.Role == 10 and removed_user:
        await callback.bot.unban_chat_member(
            chat_id=callback.message.chat.id, user_id=callback_data.user_id
        )

        invite_link: str = await callback.bot.export_chat_invite_link(
            chat_id=callback.message.chat.id
        )

        await callback.message.answer(f"""<b>🔑 Разблокировка</b>

Администратор {user.FIO} разблокировал пользователя {removed_user.FIO}
Используйте ссылку <code>{invite_link}</code> для повторного приглашения""")
        await callback.message.edit_reply_markup(
            inline_message_id=str(callback.message.message_id),
            reply_markup=on_user_leave_kb(
                user_id=callback_data.user_id,
                unban=False,
            ),
        )

    else:
        await callback.answer("У тебя недостаточно прав 🥺")
        return
    await callback.answer()


@group_events_router.callback_query(RemovedUser.filter(F.action == "change_role"))
async def change_user_role(
    callback: CallbackQuery,
    callback_data: RemovedUser,
    user: User,
    main_repo: RequestsRepo,
):
    removed_user: User = await main_repo.users.get_user(callback_data.user_id)

    if user.Role == 10 and removed_user:
        await callback.bot.unban_chat_member(
            chat_id=callback.message.chat.id, user_id=callback_data.user_id
        )

        await main_repo.users.update_user_role(
            user_id=callback_data.user_id, role=callback_data.role
        )

        invite_link: str = await callback.bot.export_chat_invite_link(
            chat_id=callback.message.chat.id
        )

        await callback.message.answer(
            f"""<b>Разблокировка</b>

Администратор {user.FIO} разблокировал пользователя {removed_user.FIO}

Теперь {removed_user.FIO} имеет роль {role_names[removed_user.Role]}
Используйте ссылку <code>{invite_link}</code> для повторного приглашения""",
            reply_markup=on_user_leave_kb(
                user_id=callback.message.chat.id, change_role=True, unban=False
            ),
        )
        await callback.message.edit_reply_markup(
            inline_message_id=str(callback.message.message_id),
            reply_markup=on_user_leave_kb(
                user_id=callback_data.user_id,
                unban=False,
            ),
        )

    else:
        await callback.answer("У тебя недостаточно прав 🥺")
        return
    await callback.answer()
