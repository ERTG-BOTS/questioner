import datetime
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    CallbackQuery,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
    ReplyKeyboardRemove,
)

from infrastructure.database.models import MessagesPair, Question, User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.active_question import ActiveQuestion, ActiveQuestionWithCommand
from tgbot.keyboards.group.main import question_quality_duty_kb
from tgbot.keyboards.user.main import (
    QuestionQualitySpecialist,
    closed_question_specialist_kb,
    question_quality_specialist_kb,
)
from tgbot.middlewares.message_pairing import store_message_connection
from tgbot.misc import dicts
from tgbot.misc.helpers import check_premium_emoji
from tgbot.services.logger import setup_logging
from tgbot.services.scheduler import (
    restart_inactivity_timer,
    run_delete_timer,
    stop_inactivity_timer,
)

user_q_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@user_q_router.message(ActiveQuestionWithCommand("end"))
async def active_question_end(
    message: Message,
    questions_repo: RequestsRepo,
    user: User,
    question: Question,
):
    if question is not None:
        if question.status != "closed":
            # Останавливаем таймер бездействия
            stop_inactivity_timer(question.token)

            await questions_repo.questions.update_question_status(
                token=question.token, status="closed"
            )
            await questions_repo.questions.update_question_end(
                token=question.token, end_time=datetime.datetime.now()
            )

            if question.quality_duty is not None:
                if question.quality_duty:
                    await message.bot.send_message(
                        chat_id=config.tg_bot.ntp_forum_id
                        if "НТП" in user.Division
                        else config.tg_bot.nck_forum_id,
                        message_thread_id=question.topic_id,
                        text=f"""<b>🔒 Вопрос закрыт</b>
    
Специалист <b>{user.FIO}</b> закрыл вопрос
👍 Специалист <b>не мог решить вопрос самостоятельно</b>""",
                        reply_markup=question_quality_duty_kb(
                            token=question.token,
                            show_quality=None,
                            allow_return=question.allow_return,
                        ),
                    )
                else:
                    await message.bot.send_message(
                        chat_id=config.tg_bot.ntp_forum_id
                        if "НТП" in user.Division
                        else config.tg_bot.nck_forum_id,
                        message_thread_id=question.topic_id,
                        text=f"""<b>🔒 Вопрос закрыт</b>

Специалист <b>{user.FIO}</b> закрыл вопрос
👎 Специалист <b>мог решить вопрос самостоятельно</b>""",
                        reply_markup=question_quality_duty_kb(
                            token=question.token,
                            show_quality=None,
                            allow_return=question.allow_return,
                        ),
                    )
            else:
                await message.bot.send_message(
                    chat_id=config.tg_bot.ntp_forum_id
                    if "НТП" in user.Division
                    else config.tg_bot.nck_forum_id,
                    message_thread_id=question.topic_id,
                    text=f"""<b>🔒 Вопрос закрыт</b>

Специалист <b>{user.FIO}</b> закрыл вопрос
Оцени, мог ли специалист решить его самостоятельно""",
                    reply_markup=question_quality_duty_kb(
                        token=question.token,
                        show_quality=True,
                        allow_return=question.allow_return,
                    ),
                )

            await message.bot.edit_forum_topic(
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in user.Division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
                name=question.token,
                icon_custom_emoji_id=dicts.topicEmojis["closed"],
            )
            await message.bot.close_forum_topic(
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in user.Division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
            )

            await message.reply(
                text="<b>🔒 Вопрос закрыт</b>", reply_markup=ReplyKeyboardRemove()
            )
            await message.answer(
                """Ты закрыл вопрос
Оцени, помогли ли тебе решить вопрос""",
                reply_markup=question_quality_specialist_kb(token=question.token),
            )

            logger.info(
                f"[Вопрос] - [Закрытие] Пользователь {message.from_user.username} ({message.from_user.id}): Закрыт вопрос {question.token} со старшим {question.topic_duty_fullname}"
            )
        elif question.status == "closed":
            await message.bot.edit_forum_topic(
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in user.Division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
                name=question.token,
                icon_custom_emoji_id=dicts.topicEmojis["closed"],
            )
            await message.reply("<b>🔒 Вопрос был закрыт</b>")
            await message.bot.close_forum_topic(
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in user.Division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
            )
            logger.info(
                f"[Вопрос] - [Закрытие] Пользователь {message.from_user.username} ({message.from_user.id}): Неудачная попытка закрытия вопроса {question.token} со старшим {question.topic_duty_fullname}. Вопрос уже закрыт"
            )

    else:
        await message.answer("""<b>⚠️ Ошибка</b>

Не удалось найти вопрос в базе""")
        logger.error(
            f"[Вопрос] - [Закрытие] Пользователь {message.from_user.username} ({message.from_user.id}): Попытка закрытия вопроса неуспешна. Не удалось найти вопрос в базе с TopicId = {message.message_id}"
        )


@user_q_router.message(ActiveQuestion())
async def active_question(
    message: Message,
    questions_repo: RequestsRepo,
    user: User,
    question: Question,
) -> None:
    if message.text == "✅️ Закрыть вопрос":
        await active_question_end(
            message=message,
            questions_repo=questions_repo,
            user=user,
            question=question,
        )
        return

    # Перезапускаем таймер бездействия при сообщении от пользователя
    await restart_inactivity_timer(
        question_token=question.token, bot=message.bot, questions_repo=questions_repo
    )

    # Если реплай - пробуем отправить ответом
    if message.reply_to_message:
        # Находим связь с отвеченным сообщением
        message_pair = await questions_repo.messages_pairs.find_by_user_message(
            user_chat_id=message.chat.id,
            user_message_id=message.reply_to_message.message_id,
        )

        if message_pair:
            # Копируем с ответом если нашли связь
            copied_message = await message.bot.copy_message(
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in user.Division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
                reply_to_message_id=message_pair.topic_message_id,
            )
            logger.info(
                f"[Вопрос] - [Ответ] Найдена связь для ответа: {message.chat.id}:{message.reply_to_message.message_id} -> {message_pair.topic_chat_id}:{message_pair.topic_message_id}"
            )
        else:
            # Не найдено связи, просто копируем
            copied_message = await message.bot.copy_message(
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in user.Division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
            )
    else:
        copied_message = await message.bot.copy_message(
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
            message_thread_id=question.topic_id,
        )

    # Сохраняем коннект сообщений
    try:
        await store_message_connection(
            questions_repo=questions_repo,
            user_chat_id=message.chat.id,
            user_message_id=message.message_id,
            topic_chat_id=int(
                config.tg_bot.ntp_forum_id
                if "НТП" in user.Division
                else config.tg_bot.nck_forum_id
            ),
            topic_message_id=copied_message.message_id,
            topic_thread_id=question.topic_id,
            question_token=question.token,
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
        f"[Вопрос] - [Общение] Токен: {question.token} | Специалист: {question.employee_fullname} | Сообщение: {message.text}"
    )


@user_q_router.edited_message(ActiveQuestion())
async def handle_edited_message(
    message: Message,
    active_question_token: str,
    questions_repo: RequestsRepo,
    user: User,
    question: Question,
) -> None:
    """Универсальный хендлер для редактируемых сообщений пользователей в активных вопросах"""
    if not question:
        logger.error(
            f"[Редактирование] Не найден вопрос с токеном {active_question_token}"
        )
        return

    # Проверяем, что вопрос все еще активен
    if question.status == "closed":
        logger.warning(
            f"[Редактирование] Специалист {user.FIO} попытался редактировать сообщение в закрытом вопросе {question.token}"
        )
        return

    # Находим сообщение-пару для редактирования
    pair_to_edit: MessagesPair = await questions_repo.messages_pairs.find_pair_for_edit(
        chat_id=message.chat.id, message_id=message.message_id
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

Специалист {user.FIO} отредактировал <a href='https://t.me/c/{config.tg_bot.ntp_forum_id if "НТП" in user.Division else config.tg_bot.nck_forum_id[4:]}/{pair_to_edit.topic_thread_id}/{pair_to_edit.topic_message_id}'>сообщение</a>""",
                reply_to_message_id=pair_to_edit.topic_message_id,
            )

            logger.info(
                f"[Редактирование] Медиа сообщение специалиста отредактировано в вопросе {question.token}"
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

Специалист <b>{user.FIO}</b> отредактировал <a href='https://t.me/c/{config.tg_bot.ntp_forum_id if "НТП" in user.Division else config.tg_bot.nck_forum_id[4:]}/{pair_to_edit.topic_thread_id}/{pair_to_edit.topic_message_id}'>сообщение</a>""",
                reply_to_message_id=pair_to_edit.topic_message_id,
            )

            logger.info(
                f"[Редактирование] Текстовое сообщение специалиста отредактировано в вопросе {question.token}"
            )

        else:
            logger.warning(
                "[Редактирование] Сообщение не содержит ни текста, ни медиа для редактирования"
            )

    except TelegramAPIError as e:
        logger.error(
            f"[Редактирование] Ошибка при редактировании сообщения специалиста в вопросе {question.token}: {e}"
        )
    except Exception as e:
        logger.error(
            f"[Редактирование] Неожиданная ошибка при редактировании сообщения специалиста: {e}"
        )


@user_q_router.callback_query(
    QuestionQualitySpecialist.filter(F.return_question == False)
)
async def question_quality_employee(
    callback: CallbackQuery,
    callback_data: QuestionQualitySpecialist,
    questions_repo: RequestsRepo,
):
    question: Question = await questions_repo.questions.update_question_quality(
        token=callback_data.token, quality=callback_data.answer, is_duty=False
    )

    await callback.answer("Оценка успешно выставлена ❤️")
    if callback_data.answer:
        await callback.message.edit_text(
            """Ты поставил оценку:
👍 Дежурный <b>помог решить твой вопрос</b>""",
            reply_markup=closed_question_specialist_kb(token=callback_data.token),
        )
    else:
        await callback.message.edit_text(
            """Ты поставил оценку:
👎 Дежурный <b>не помог решить твой вопрос</b>""",
            reply_markup=closed_question_specialist_kb(token=callback_data.token),
        )
    logger.info(
        f"[Вопрос] - [Оценка] Пользователь {callback.from_user.username} ({callback.from_user.id}): Выставлена оценка {callback_data.answer} вопросу {question.token} от специалиста"
    )
    await callback.answer()
