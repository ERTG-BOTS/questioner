import datetime
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
)

from infrastructure.database.models import Question, User, QuestionConnection
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.active_question import ActiveQuestion, ActiveQuestionWithCommand
from tgbot.keyboards.group.main import dialog_quality_duty_kb
from tgbot.keyboards.user.main import (
    QuestionQualitySpecialist,
    dialog_quality_specialist_kb,
    closed_dialog_specialist_kb,
)
from tgbot.misc import dicts
from tgbot.misc.helpers import check_premium_emoji
from tgbot.services.logger import setup_logging
from tgbot.services.scheduler import (
    restart_inactivity_timer,
    run_delete_timer,
    stop_inactivity_timer,
)
from tgbot.middlewares.message_pairing import store_message_connection

user_q_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@user_q_router.message(ActiveQuestionWithCommand("end"))
async def active_question_end(
    message: Message, repo: RequestsRepo, user: User, active_dialog_token: str = None
):
    question: Question = await repo.questions.get_question(token=active_dialog_token)

    if question is not None:
        if question.Status != "closed":
            # Останавливаем таймер неактивности
            stop_inactivity_timer(question.Token)

            await repo.questions.update_question_status(
                token=question.Token, status="closed"
            )
            await repo.questions.update_question_end(
                token=question.Token, end_time=datetime.datetime.now()
            )

            if question.QualityDuty is not None:
                if question.QualityDuty:
                    await message.bot.send_message(
                        chat_id=config.tg_bot.forum_id,
                        message_thread_id=question.TopicId,
                        text=f"""<b>🔒 Вопрос закрыт</b>
    
Специалист <b>{user.FIO}</b> закрыл вопрос
👍 Специалист <b>не мог решить вопрос самостоятельно</b>""",
                        reply_markup=dialog_quality_duty_kb(
                            token=question.Token,
                            show_quality=None,
                            allow_return=question.AllowReturn,
                        ),
                    )
                else:
                    await message.bot.send_message(
                        chat_id=config.tg_bot.forum_id,
                        message_thread_id=question.TopicId,
                        text=f"""<b>🔒 Вопрос закрыт</b>

Специалист <b>{user.FIO}</b> закрыл вопрос
👎 Специалист <b>мог решить вопрос самостоятельно</b>""",
                        reply_markup=dialog_quality_duty_kb(
                            token=question.Token,
                            show_quality=None,
                            allow_return=question.AllowReturn,
                        ),
                    )
            else:
                await message.bot.send_message(
                    chat_id=config.tg_bot.forum_id,
                    message_thread_id=question.TopicId,
                    text=f"""<b>🔒 Вопрос закрыт</b>

Специалист <b>{user.FIO}</b> закрыл вопрос
Оцени, мог ли специалист решить его самостоятельно""",
                    reply_markup=dialog_quality_duty_kb(
                        token=question.Token,
                        show_quality=True,
                        allow_return=question.AllowReturn,
                    ),
                )

            await message.bot.edit_forum_topic(
                chat_id=config.tg_bot.forum_id,
                message_thread_id=question.TopicId,
                name=question.Token,
                icon_custom_emoji_id=dicts.topicEmojis["closed"],
            )
            await message.bot.close_forum_topic(
                chat_id=config.tg_bot.forum_id, message_thread_id=question.TopicId
            )

            await message.reply(
                text="<b>🔒 Вопрос закрыт</b>", reply_markup=ReplyKeyboardRemove()
            )
            await message.answer(
                """Ты закрыл вопрос
Оцени, помогли ли тебе решить вопрос""",
                reply_markup=dialog_quality_specialist_kb(token=question.Token),
            )

            logger.info(
                f"[Вопрос] - [Закрытие] Пользователь {message.from_user.username} ({message.from_user.id}): Закрыт вопрос {question.Token} со старшим {question.TopicDutyFullname}"
            )
        elif question.Status == "closed":
            await message.reply("<b>🔒 Вопрос был закрыт</b>")
            await message.bot.close_forum_topic(
                chat_id=config.tg_bot.forum_id, message_thread_id=question.TopicId
            )
            logger.info(
                f"[Вопрос] - [Закрытие] Пользователь {message.from_user.username} ({message.from_user.id}): Неудачная попытка закрытия вопроса {question.Token} со старшим {question.TopicDutyFullname}. Вопрос уже закрыт"
            )

    else:
        await message.answer("""<b>⚠️ Ошибка</b>

Не удалось найти вопрос в базе""")
        logger.error(
            f"[Вопрос] - [Закрытие] Пользователь {message.from_user.username} ({message.from_user.id}): Попытка закрытия вопроса неуспешна. Не удалось найти вопрос в базе с TopicId = {message.message_id}"
        )


@user_q_router.message(ActiveQuestion())
async def active_question(
    message: Message, active_dialog_token: str, repo: RequestsRepo
) -> None:
    question: Question = await repo.questions.get_question(token=active_dialog_token)

    if message.text == "✅️ Закрыть вопрос":
        await active_question_end(
            message=message, repo=repo, active_dialog_token=active_dialog_token
        )
        return

    # Перезапускаем таймер неактивности при сообщении от пользователя
    await restart_inactivity_timer(
        question_token=question.Token, bot=message.bot, repo=repo
    )

    copied_message = await message.bot.copy_message(
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        chat_id=config.tg_bot.forum_id,
        message_thread_id=question.TopicId,
    )

    # Сохраняем коннект сообщений
    try:
        await store_message_connection(
            repo=repo,
            user_chat_id=message.chat.id,
            user_message_id=message.message_id,
            topic_chat_id=int(config.tg_bot.forum_id),
            topic_message_id=copied_message.message_id,
            topic_thread_id=question.TopicId,
            question_token=question.Token,
            direction="user_to_topic",
        )
    except Exception as e:
        logger.error(f"Failed to store message connection: {e}")

    # Уведомление о премиум эмодзи
    have_premium_emoji, emoji_ids = await check_premium_emoji(message)
    if have_premium_emoji and emoji_ids:
        emoji_sticker_list = await message.bot.get_custom_emoji_stickers(emoji_ids)

        sticker_info = []
        for emoji_sticker in emoji_sticker_list:
            sticker_info.append(f"{emoji_sticker.emoji}")

        stickers_text = "".join(sticker_info)

        emoji_message = await message.reply(f"""<b>💎 Премиум эмодзи</b>

Сообщение содержит премиум эмодзи, собеседник увидит бесплатные аналоги: {stickers_text}

<i>Предупреждение удалится через 30 секунд</i>""")
        await run_delete_timer(
            bot=message.bot,
            chat_id=message.chat.id,
            message_ids=[emoji_message.message_id],
            seconds=30,
        )

    logger.info(
        f"[Вопрос] - [Общение] Токен: {question.Token} | Специалист: {question.EmployeeFullname} | Сообщение: {message.text}"
    )


@user_q_router.edited_message(ActiveQuestion())
async def handle_edited_message(
    message: Message, active_dialog_token: str, repo: RequestsRepo, user: User
) -> None:
    """Универсальный хендлер для редактируемых сообщений пользователей в активных вопросах"""

    question: Question = await repo.questions.get_question(token=active_dialog_token)

    if not question:
        logger.error(
            f"[Редактирование] Не найден вопрос с токеном {active_dialog_token}"
        )
        return

    # Проверяем, что вопрос все еще активен
    if question.Status == "closed":
        logger.warning(
            f"[Редактирование] Специалист {user.FIO} попытался редактировать сообщение в закрытом вопросе {question.Token}"
        )
        return

    # Находим сообщение-пару для редактирования
    pair_to_edit: QuestionConnection = (
        await repo.questions_connections.find_pair_for_edit(
            chat_id=message.chat.id, message_id=message.message_id
        )
    )

    if not pair_to_edit:
        logger.warning(
            f"[Редактирование] Не найдена пара сообщений для редактирования: {message.chat.id}:{message.message_id}"
        )
        return

    edit_timestamp = f"\n\n<i>Сообщение изменено специалистом — {datetime.datetime.now().strftime('%H:%M %d.%m.%Y')}</i>"

    try:
        # Проверяем сообщение на содержание медиа
        if any(
            [
                message.photo,
                message.video,
                message.document,
                message.audio,
                message.animation,
            ]
        ):
            new_media = None

            if message.animation:
                new_media = InputMediaAnimation(media=message.animation.file_id)
            elif message.audio:
                new_media = InputMediaAudio(media=message.audio.file_id)
            elif message.document:
                new_media = InputMediaDocument(media=message.document.file_id)
            elif message.photo:
                new_media = InputMediaPhoto(media=message.photo[-1].file_id)
            elif message.video:
                new_media = InputMediaVideo(media=message.video.file_id)

            if not new_media:
                logger.warning(
                    "[Редактирование] Неподдерживаемый тип медиа для редактирования"
                )
                return

            # Устанавливаем caption с меткой времени редактирования
            if message.caption:
                new_media.caption = message.caption + edit_timestamp
                new_media.caption_entities = message.caption_entities
            else:
                new_media.caption = edit_timestamp.strip()

            # Редактирование медиа в чате со специалистом
            await message.bot.edit_message_media(
                chat_id=pair_to_edit.topic_chat_id,
                message_id=pair_to_edit.topic_message_id,
                media=new_media,
            )

            # Уведомление дежурного об изменении сообщения специалистом
            await message.bot.send_message(
                chat_id=pair_to_edit.topic_chat_id,
                message_thread_id=pair_to_edit.topic_thread_id,
                text=f"""<b>♻️ Изменение сообщения</b>

Специалист {user.FIO} отредактировал <a href='https://t.me/c/{config.tg_bot.forum_id[4:]}/{pair_to_edit.topic_thread_id}/{pair_to_edit.topic_message_id}'>сообщение</a>""",
            )

            logger.info(
                f"[Редактирование] Медиа сообщение специалиста отредактировано в вопросе {question.Token}"
            )

        elif message.text:
            # Обрабатываем текстовые сообщения
            await message.bot.edit_message_text(
                chat_id=pair_to_edit.topic_chat_id,
                message_id=pair_to_edit.topic_message_id,
                text=message.text + edit_timestamp,
            )

            # Уведомление дежурного об изменении сообщения специалистом
            await message.bot.send_message(
                chat_id=pair_to_edit.topic_chat_id,
                message_thread_id=pair_to_edit.topic_thread_id,
                text=f"""<b>♻️ Изменение сообщения</b>

Специалист <b>{user.FIO}</b> отредактировал <a href='https://t.me/c/{config.tg_bot.forum_id[4:]}/{pair_to_edit.topic_thread_id}/{pair_to_edit.topic_message_id}'>сообщение</a>""",
            )

            logger.info(
                f"[Редактирование] Текстовое сообщение специалиста отредактировано в вопросе {question.Token}"
            )

        else:
            logger.warning(
                "[Редактирование] Сообщение не содержит ни текста, ни медиа для редактирования"
            )

    except TelegramAPIError as e:
        logger.error(
            f"[Редактирование] Ошибка при редактировании сообщения специалиста в вопросе {question.Token}: {e}"
        )
    except Exception as e:
        logger.error(
            f"[Редактирование] Неожиданная ошибка при редактировании сообщения специалиста: {e}"
        )


@user_q_router.callback_query(
    QuestionQualitySpecialist.filter(F.return_question == False)
)
async def dialog_quality_employee(
    callback: CallbackQuery,
    callback_data: QuestionQualitySpecialist,
    repo: RequestsRepo,
):
    question: Question = await repo.questions.get_question(token=callback_data.token)
    await repo.questions.update_question_quality(
        token=callback_data.token, quality=callback_data.answer, is_duty=False
    )

    await callback.answer("Оценка успешно выставлена ❤️")
    if callback_data.answer:
        await callback.message.edit_text(
            """Ты поставил оценку:
👍 Старший <b>помог решить твой вопрос</b>""",
            reply_markup=closed_dialog_specialist_kb(token=callback_data.token),
        )
    else:
        await callback.message.edit_text(
            """Ты поставил оценку:
👎 Старший <b>не помог решить твой вопрос</b>""",
            reply_markup=closed_dialog_specialist_kb(token=callback_data.token),
        )
    logger.info(
        f"[Вопрос] - [Оценка] Пользователь {callback.from_user.username} ({callback.from_user.id}): Выставлена оценка {callback_data.answer} вопросу {question.Token} от специалиста"
    )
