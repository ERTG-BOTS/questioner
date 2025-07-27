import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram.types import BotCommand

from infrastructure.database.setup import create_engine, create_session_pool
from tgbot.config import Config, load_config
from tgbot.handlers import routers_list
from tgbot.middlewares.config import ConfigMiddleware
from tgbot.middlewares.database import DatabaseMiddleware
from tgbot.middlewares.message_pairing import MessagePairingMiddleware
from tgbot.services.logger import setup_logging
from tgbot.services.scheduler import remove_old_topics, scheduler

bot_config = load_config(".env")

logger = logging.getLogger(__name__)


# async def on_startup(bot: Bot):
#     if bot_config.tg_bot.activity_status:
#         timeout_msg = f"Да ({bot_config.tg_bot.activity_warn_minutes}/{bot_config.tg_bot.activity_close_minutes} минут)"
#     else:
#         timeout_msg = "Нет"
#
#     if bot_config.tg_bot.remove_old_questions:
#         remove_topics_msg = (
#             f"Да (старше {bot_config.tg_bot.remove_old_questions_days} дней)"
#         )
#     else:
#         remove_topics_msg = "Нет"
#
#     await bot.send_message(
#         chat_id=bot_config.tg_bot.ntp_forum_id,
#         text=f"""<b>🚀 Запуск</b>
#
# Вопросник запущен со следующими параметрами:
# <b>- Направление:</b> {bot_config.tg_bot.division}
# <b>- Запрашивать регламент:</b> {"Да" if bot_config.tg_bot.ask_clever_link else "Нет"}
# <b>- Закрывать по таймауту:</b> {timeout_msg}
# <b>- Удалять старые вопросы:</b> {remove_topics_msg}
#
# <blockquote>База данных: {"Основная" if bot_config.db.main_db == "STPMain" else "Запасная"}</blockquote>""",
#     )


def register_global_middlewares(
    dp: Dispatcher,
    config: Config,
    bot: Bot,
    main_session_pool=None,
    questioner_session_pool=None,
):
    """
    Register global middlewares for the given dispatcher.
    Global middlewares here are the ones that are applied to all the handlers (you specify the type of update)

    :param bot: Bot object.
    :param dp: The dispatcher instance.
    :type dp: Dispatcher
    :param config: The configuration object from the loaded configuration.
    :param session_pool: Optional session pool object for the database using SQLAlchemy.
    :return: None
    """
    middleware_types = [
        ConfigMiddleware(config),
        DatabaseMiddleware(
            config=config,
            bot=bot,
            main_session_pool=main_session_pool,
            questioner_session_pool=questioner_session_pool,
        ),
    ]

    for middleware_type in middleware_types:
        dp.message.outer_middleware(middleware_type)
        dp.callback_query.outer_middleware(middleware_type)
        dp.edited_message.outer_middleware(middleware_type)
        dp.chat_member.outer_middleware(middleware_type)

    dp.edited_message.outer_middleware(MessagePairingMiddleware())


def get_storage(config):
    """
    Return storage based on the provided configuration.

    Args:
        config (Config): The configuration object.

    Returns:
        Storage: The storage object based on the configuration.

    """
    if config.tg_bot.use_redis:
        return RedisStorage.from_url(
            config.redis.dsn(),
            key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
        )
    else:
        return MemoryStorage()


async def main():
    setup_logging()

    storage = get_storage(bot_config)

    bot = Bot(
        token=bot_config.tg_bot.token, default=DefaultBotProperties(parse_mode="HTML")
    )
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Главное меню"),
            BotCommand(
                command="release", description="Освободить вопрос (для старших)"
            ),
            BotCommand(command="end", description="Закрыть вопрос"),
        ]
    )

    # TODO Установить универсальное название при запуске бота
    # await bot.set_my_name(name="Вопросник")

    dp = Dispatcher(storage=storage)

    # Create engines for different databases
    stp_db_engine = create_engine(bot_config.db, db_name=bot_config.db.main_db)
    questioner_db_engine = create_engine(
        bot_config.db, db_name=bot_config.db.questioner_db
    )

    stp_db = create_session_pool(stp_db_engine)
    questioner_db = create_session_pool(questioner_db_engine)

    # Store session pools in dispatcher
    dp["stp_db"] = stp_db
    dp["questioner_db"] = questioner_db

    dp.include_routers(*routers_list)

    register_global_middlewares(dp, bot_config, bot, stp_db, questioner_db)

    if bot_config.tg_bot.remove_old_questions:
        scheduler.add_job(
            remove_old_topics, "interval", hours=12, args=[bot, questioner_db]
        )
    await remove_old_topics(bot, questioner_db)
    scheduler.start()

    # await on_startup(bot)
    try:
        await dp.start_polling(bot)
    finally:
        await stp_db_engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot was interrupted by the user!")
