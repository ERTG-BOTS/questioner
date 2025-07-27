import datetime
import logging

import pytz
from aiogram import Bot
from aiogram.types import ReplyKeyboardRemove
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import Sequence

from infrastructure.database.models import MessagesPair, Question
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.keyboards.group.main import closed_question_duty_kb
from tgbot.keyboards.user.main import closed_question_specialist_kb
from tgbot.misc import dicts
from tgbot.services.logger import setup_logging

scheduler = AsyncIOScheduler(timezone=pytz.utc)
config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


async def delete_messages(bot: Bot, chat_id: int, message_ids: list[int]):
    """Удаляет список сообщений."""
    try:
        for message_id in message_ids:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Ошибка при удалении сообщений: {e}")


async def run_delete_timer(
    bot: Bot, chat_id: int, message_ids: list[int], seconds: int = 60
):
    """Delete messages after timer. Default - 60 seconds."""
    try:
        scheduler.add_job(
            delete_messages,
            "date",
            run_date=datetime.datetime.now(tz=pytz.utc)
            + datetime.timedelta(seconds=seconds),
            args=[bot, chat_id, message_ids],
        )
    except Exception as e:
        print(f"Ошибка при планировании удаления сообщений: {e}")


async def remove_question_timer(bot: Bot, question: Question):
    warning_job_id = f"remove_{question.token}"
    scheduler.add_job(
        remove_question,
        "date",
        run_date=datetime.datetime.now(tz=pytz.utc) + datetime.timedelta(seconds=30),
        args=[bot, question],
        id=warning_job_id,
    )


async def remove_question(bot: Bot, question: Question):
    await bot.delete_forum_topic(
        chat_id=config.tg_bot.ntp_forum_id
        if "НТП" in question.employee_division
        else config.tg_bot.nck_forum_id,
        message_thread_id=question.topic_id,
    )


async def remove_old_topics(bot: Bot, session_pool):
    # Create a session and RequestsRepo instance
    async with session_pool() as session:
        questions_repo = RequestsRepo(session)

        old_questions: Sequence[
            Question
        ] = await questions_repo.questions.get_old_questions()
        old_pairs: Sequence[
            MessagesPair
        ] = await questions_repo.messages_pairs.get_old_pairs()

        questions_result = await questions_repo.questions.delete_question(
            questions=old_questions
        )

        for question in old_questions:
            await bot.delete_forum_topic(
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in question.employee_division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
            )

        pairs_result = await questions_repo.messages_pairs.delete_pairs(pairs=old_pairs)
        logger.info(
            f"[Старые топики] Успешно удалено {questions_result['deleted_count']} из {questions_result['total_count']} старых вопросов"
        )
        logger.info(
            f"[Старые пары] Успешно удалено {pairs_result['deleted_count']} из {pairs_result['total_count']} старых пар сообщений"
        )

        if questions_result["errors"]:
            logger.info(
                f"[Старые топики] Произошла ошибка при удалении части вопросов: {questions_result['errors']}"
            )
        if pairs_result["errors"]:
            logger.info(
                f"[Старые пары] Произошла ошибка при удалении части пар: {pairs_result['errors']}"
            )


async def send_inactivity_warning(
    bot: Bot, question_token: str, questions_repo: RequestsRepo
):
    """Отправляет предупреждение о бездействии через 5 минут."""
    try:
        question: Question = await questions_repo.questions.get_question(
            token=question_token
        )

        if question and question.status in ["open", "in_progress"]:
            # Отправляем предупреждение в топик
            await bot.send_message(
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in question.employee_division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
                text="⚠️ <b>Внимание!</b>\n\nЧат будет автоматически закрыт через 5 минут при отсутствии активности",
            )

            # Отправляем предупреждение пользователю
            await bot.send_message(
                chat_id=question.employee_chat_id,
                text="⚠️ <b>Внимание!</b>\n\nТвой вопрос будет автоматически закрыт через 5 минут при отсутствии активности",
            )

    except Exception as e:
        logger.error(
            f"[Таймер бездействия] Ошибка при отправке предупреждения для вопроса {question_token}: {e}"
        )


async def auto_close_question(
    bot: Bot, question_token: str, questions_repo: RequestsRepo
):
    """Автоматически закрывает вопрос через 10 минут бездействия."""
    try:
        question: Question = await questions_repo.questions.get_question(
            token=question_token
        )

        if question and question.status in ["open", "in_progress"]:
            # Закрываем вопрос
            await questions_repo.questions.update_question_status(
                token=question_token, status="closed"
            )
            await questions_repo.questions.update_question_end(
                token=question_token, end_time=datetime.datetime.now()
            )

            # Уведомляем о закрытии
            await bot.send_message(
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in question.employee_division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
                text="🔒 <b>Вопрос автоматически закрыт</b>\n\nВопрос был закрыт из-за отсутствия активности в течение 10 минут",
                reply_markup=closed_question_duty_kb(token=question_token),
            )

            # Обновляем топик
            await bot.edit_forum_topic(
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in question.employee_division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
                name=question.token,
                icon_custom_emoji_id=dicts.topicEmojis["closed"],
            )
            await bot.close_forum_topic(
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in question.employee_division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
            )

            await bot.send_message(
                chat_id=question.employee_chat_id,
                text="🔒 <b>Вопрос автоматически закрыт</b>",
                reply_markup=ReplyKeyboardRemove(),
            )
            await bot.send_message(
                chat_id=question.employee_chat_id,
                text="Твой вопрос был закрыт из-за отсутствия активности в течение 10 минут",
                reply_markup=closed_question_specialist_kb(token=question_token),
            )

    except Exception as e:
        logger.error(
            f"[Таймер бездействия] Ошибка при автоматическом закрытии вопроса {question_token}: {e}"
        )


async def start_inactivity_timer(
    question_token: str, bot: Bot, questions_repo: RequestsRepo
):
    """Запускает таймер бездействия для вопроса."""
    try:
        # Проверяем, нужно ли запускать тайметр для этого вопроса
        question = await questions_repo.questions.get_question(token=question_token)
        if not question:
            return

        # Определяем эффективный статус активности
        activity_enabled = (
            question.activity_status_enabled
            if question.activity_status_enabled is not None
            else config.tg_bot.activity_status
        )

        if not activity_enabled:
            # Если активность отключена для этого топика, не запускаем таймер
            return

        # Удаляем существующие задачи для этого вопроса
        stop_inactivity_timer(question_token)

        # Запускаем таймер предупреждения (5 минут)
        warning_job_id = f"warning_{question_token}"
        scheduler.add_job(
            send_inactivity_warning,
            "date",
            run_date=datetime.datetime.now(tz=pytz.utc)
            + datetime.timedelta(minutes=config.tg_bot.activity_warn_minutes),
            args=[bot, question_token, questions_repo],
            id=warning_job_id,
        )

        # Запускаем таймер автозакрытия (10 минут)
        close_job_id = f"close_{question_token}"
        scheduler.add_job(
            auto_close_question,
            "date",
            run_date=datetime.datetime.now(tz=pytz.utc)
            + datetime.timedelta(minutes=config.tg_bot.activity_close_minutes),
            args=[bot, question_token, questions_repo],
            id=close_job_id,
        )

    except Exception as e:
        logger.error(
            f"[Таймер бездействия] Ошибка при запуске таймера для вопроса {question_token}: {e}"
        )


def stop_inactivity_timer(question_token: str):
    """Останавливает таймер бездействия для вопроса."""
    try:
        warning_job_id = f"warning_{question_token}"
        close_job_id = f"close_{question_token}"

        # Удаляем задачи если они существуют
        if scheduler.get_job(job_id=warning_job_id):
            scheduler.remove_job(job_id=warning_job_id)

        if scheduler.get_job(job_id=close_job_id):
            scheduler.remove_job(job_id=close_job_id)

    except Exception as e:
        logger.error(
            f"[Таймер бездействия] Ошибка при остановке таймера для вопроса {question_token}: {e}"
        )


async def restart_inactivity_timer(
    question_token: str, bot: Bot, questions_repo: RequestsRepo
):
    """Перезапускает таймер бездействия для вопроса."""
    stop_inactivity_timer(question_token=question_token)
    await start_inactivity_timer(
        question_token=question_token, bot=bot, questions_repo=questions_repo
    )
