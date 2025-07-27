import logging
from datetime import datetime
from typing import Sequence

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
)

from infrastructure.database.models import MessagesPair, Question, User
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import load_config
from tgbot.filters.topic import IsTopicMessage
from tgbot.handlers.group.cmds import end_q_cmd
from tgbot.keyboards.group.main import (
    QuestionAllowReturn,
    QuestionQualityDuty,
    closed_question_duty_kb,
    question_quality_duty_kb,
    duty_start,
)
from tgbot.keyboards.user.main import (
    finish_question_kb,
)
from tgbot.middlewares.message_pairing import store_message_connection
from tgbot.misc import dicts
from tgbot.misc.helpers import check_premium_emoji
from tgbot.services.logger import setup_logging
from tgbot.services.scheduler import (
    restart_inactivity_timer,
    run_delete_timer,
    start_inactivity_timer,
)

topic_router = Router()

config = load_config(".env")

setup_logging()
logger = logging.getLogger(__name__)


@topic_router.message(IsTopicMessage())
async def handle_q_message(
    message: Message,
    user: User,
    questions_repo: RequestsRepo,
    main_repo: RequestsRepo,
    question: Question,
):
    if message.text == "✅️ Закрыть вопрос":
        await end_q_cmd(
            message=message,
            user=user,
            questions_repo=questions_repo,
            main_repo=main_repo,
            question=question,
        )
        return

    if question is not None and question.status != "closed":
        if not question.topic_duty_fullname:
            duty_topics_today = (
                await questions_repo.questions.get_questions_count_today(
                    duty_fullname=user.FIO
                )
            )
            duty_topics_month = (
                await questions_repo.questions.get_questions_count_last_month(
                    duty_fullname=user.FIO
                )
            )

            await questions_repo.questions.update_question_duty(
                token=question.token, topic_duty=user.FIO
            )
            await questions_repo.questions.update_question_status(
                token=question.token, status="in_progress"
            )

            employee: User = await main_repo.users.get_user(
                fullname=question.employee_fullname
            )

            # Запускаем таймер бездействия для нового вопроса
            await start_inactivity_timer(
                question_token=question.token,
                bot=message.bot,
                questions_repo=questions_repo,
            )

            await message.bot.edit_forum_topic(
                chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in user.Division
                else config.tg_bot.nck_forum_id,
                message_thread_id=question.topic_id,
                icon_custom_emoji_id=dicts.topicEmojis["in_progress"],
            )
            await message.answer(
                f"""<b>👮‍♂️ Вопрос в работе</b>

На вопрос отвечает <b>{user.FIO}</b>

<blockquote expandable><b>⚒️ Решено:</b> за день {duty_topics_today} / за месяц {duty_topics_month}</blockquote>""",
                disable_web_page_preview=True,
                reply_markup=duty_start(user_id=user.ChatId),
            )

            await message.bot.send_message(
                chat_id=employee.ChatId,
                text=f"""<b>👮‍♂️ Вопрос в работе</b>

Дежурный <b>{user.FIO}</b> взял вопрос в работу""",
                reply_markup=finish_question_kb(),
            )

            copied_message = await message.bot.copy_message(
                from_chat_id=config.tg_bot.ntp_forum_id
                if "НТП" in user.Division
                else config.tg_bot.nck_forum_id,
                message_id=message.message_id,
                chat_id=employee.ChatId,
            )

            # Сохраняем коннект сообщений
            try:
                await store_message_connection(
                    questions_repo=questions_repo,
                    user_chat_id=question.employee_chat_id,
                    user_message_id=copied_message.message_id,
                    topic_chat_id=int(
                        config.tg_bot.ntp_forum_id
                        if "НТП" in user.Division
                        else config.tg_bot.nck_forum_id
                    ),
                    topic_message_id=message.message_id,
                    topic_thread_id=question.topic_id,
                    question_token=question.token,
                    direction="topic_to_user",
                )
            except Exception as e:
                logger.error(f"Failed to store message connection: {e}")

            logger.info(
                f"[Вопрос] - [В работе] Пользователь {message.from_user.username} ({message.from_user.id}): Вопрос {question.token} взят в работу"
            )
        else:
            if question.topic_duty_fullname == user.FIO:
                # Перезапускаем таймер бездействия при сообщении от дежурного
                await restart_inactivity_timer(
                    question_token=question.token,
                    bot=message.bot,
                    questions_repo=questions_repo,
                )

                # Если реплай - пробуем отправить ответом
                if message.reply_to_message:
                    # Находим связь с отвеченным сообщением
                    message_pair = (
                        await questions_repo.messages_pairs.find_by_topic_message(
                            topic_chat_id=int(
                                config.tg_bot.ntp_forum_id
                                if "НТП" in user.Division
                                else config.tg_bot.nck_forum_id
                            ),
                            topic_message_id=message.reply_to_message.message_id,
                        )
                    )

                    if message_pair:
                        # Копируем с ответом если нашли связь
                        copied_message = await message.bot.copy_message(
                            from_chat_id=config.tg_bot.ntp_forum_id
                            if "НТП" in user.Division
                            else config.tg_bot.nck_forum_id,
                            message_id=message.message_id,
                            chat_id=question.employee_chat_id,
                            reply_to_message_id=message_pair.user_message_id,
                        )
                        logger.info(
                            f"[Вопрос] - [Ответ] Найдена связь для ответа дежурного: {config.tg_bot.ntp_forum_id if 'НТП' in user.Division else 'НЦК'}:{message.reply_to_message.message_id} -> {message_pair.user_chat_id}:{message_pair.user_message_id}"
                        )
                    else:
                        # Не найдено связи, просто копируем
                        copied_message = await message.bot.copy_message(
                            from_chat_id=config.tg_bot.ntp_forum_id
                            if "НТП" in user.Division
                            else config.tg_bot.nck_forum_id,
                            message_id=message.message_id,
                            chat_id=question.employee_chat_id,
                        )
                else:
                    copied_message = await message.bot.copy_message(
                        from_chat_id=config.tg_bot.ntp_forum_id
                        if "НТП" in user.Division
                        else config.tg_bot.nck_forum_id,
                        message_id=message.message_id,
                        chat_id=question.employee_chat_id,
                    )

                # Сохраняем коннект сообщений
                try:
                    await store_message_connection(
                        questions_repo=questions_repo,
                        user_chat_id=question.employee_chat_id,
                        user_message_id=copied_message.message_id,
                        topic_chat_id=int(
                            config.tg_bot.ntp_forum_id
                            if "НТП" in user.Division
                            else config.tg_bot.nck_forum_id
                        ),
                        topic_message_id=message.message_id,
                        topic_thread_id=question.topic_id,
                        question_token=question.token,
                        direction="topic_to_user",
                    )
                except Exception as e:
                    logger.error(f"Failed to store message connection: {e}")

                # Уведомление о премиум эмодзи
                have_premium_emoji, emoji_ids = await check_premium_emoji(message)
                if have_premium_emoji and emoji_ids:
                    emoji_sticker_list = await message.bot.get_custom_emoji_stickers(
                        emoji_ids
                    )

                    sticker_info = []
                    for emoji_sticker in emoji_sticker_list:
                        sticker_info.append(f"{emoji_sticker.emoji}")

                    stickers_text = "".join(sticker_info)

                    emoji_message = await message.reply(f"""<b>💎 Премиум эмодзи</b>

Сообщение содержит премиум эмодзи, собеседник увидит бесплатные аналоги: {stickers_text}

<i>Предупреждение удалится через 30 секунд</i>""")
                    await run_delete_timer(
                        bot=message.bot,
                        chat_id=int(
                            config.tg_bot.ntp_forum_id
                            if "НТП" in user.Division
                            else config.tg_bot.nck_forum_id
                        ),
                        message_ids=[emoji_message.message_id],
                        seconds=30,
                    )

                logger.info(
                    f"[Вопрос] - [Общение] Токен: {question.token} | Дежурный: {question.topic_duty_fullname} | Сообщение: {message.text}"
                )
            else:
                await message.reply("""<b>⚠️ Предупреждение</b>

Это не твой чат!

<i>Твое сообщение не отобразится специалисту</i>""")
                logger.warning(
                    f"[Вопрос] - [Общение] Токен: {question.token} | Дежурный: {question.topic_duty_fullname} | Сообщение: {message.text}. Чат принадлежит другому старшему"
                )
    elif question.status == "closed":
        await message.reply("""<b>⚠️ Предупреждение</b>

Текущий вопрос уже закрыт!

<i>Твое сообщение не отобразится специалисту</i>""")
        logger.warning(
            f"[Вопрос] - [Общение] Токен: {question.token} | Дежурный: {question.topic_duty_fullname} | Сообщение: {message.text}. Чат уже закрыт"
        )
    else:
        await message.answer("""<b>⚠️ Ошибка</b>

Не удалось найти текущую тему в базе, закрываю""")
        await message.bot.close_forum_topic(
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
            message_thread_id=message.message_thread_id,
        )
        logger.error(
            f"[Вопрос] - [Общение] Не удалось найти вопрос в базе с TopicId = {message.message_thread_id}. Закрыли тему"
        )


@topic_router.edited_message(IsTopicMessage())
async def handle_edited_message(
    message: Message, questions_repo: RequestsRepo, user: User, question: Question
):
    """Универсальных хендлер для редактируемых сообщений в топиках"""
    if not question:
        logger.error(
            f"[Редактирование] Не найдено вопроса для топика: {message.message_thread_id}"
        )
        return

    # Проверяем, что вопрос все еще активен
    if question.status == "closed":
        logger.warning(
            f"[Редактирование] Дежурный {user.FIO} попытался редактировать сообщение в закрытом вопросе {question.token}"
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

    edit_timestamp = f"\n\n<i>Сообщение изменено дежурным — {datetime.now().strftime('%H:%M %d.%m.%Y')}</i>"

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

            if message.caption:
                new_media.caption = message.caption + edit_timestamp
                new_media.caption_entities = message.caption_entities
            else:
                new_media.caption = edit_timestamp.strip()

            # Редактирование медиа в чате со специалистом
            await message.bot.edit_message_media(
                chat_id=pair_to_edit.user_chat_id,
                message_id=pair_to_edit.user_message_id,
                media=new_media,
            )

            # Уведомление специалиста об изменении сообщения дежурным
            await message.bot.send_message(
                chat_id=pair_to_edit.user_chat_id,
                text=f"""<b>♻️ Изменение сообщения</b>

Дежурный <b>{user.FIO}</b> отредактировал сообщение""",
                reply_to_message_id=pair_to_edit.user_message_id,
            )

            logger.info(
                f"[Редактирование] Медиа сообщение отредактировано в вопросе {question.token}"
            )

        elif message.text:
            # Обрабатываем сообщения без медиа
            await message.bot.edit_message_text(
                chat_id=pair_to_edit.user_chat_id,
                message_id=pair_to_edit.user_message_id,
                text=message.text + edit_timestamp,
            )

            # Уведомление специалиста об изменении сообщения дежурным
            await message.bot.send_message(
                chat_id=pair_to_edit.user_chat_id,
                text=f"""<b>♻️ Изменение сообщения</b>

Дежурный <b>{user.FIO}</b> отредактировал сообщение""",
                reply_to_message_id=pair_to_edit.user_message_id,
            )

            logger.info(
                f"[Редактирование] Текстовое сообщение отредактировано в вопросе {question.token}"
            )

        else:
            logger.warning(
                "[Редактирование] Сообщение не содержит ни текста, ни медиа для редактирования"
            )

    except TelegramAPIError as e:
        logger.error(
            f"[Редактирование] Ошибка при редактировании сообщения в вопросе {question.token}: {e}"
        )
    except Exception as e:
        logger.error(
            f"[Редактирование] Неожиданная ошибка при редактировании сообщения: {e}"
        )


@topic_router.callback_query(QuestionQualityDuty.filter(F.return_question))
async def return_q_duty(
    callback: CallbackQuery,
    user: User,
    questions_repo: RequestsRepo,
    question: Question,
):
    available_to_return_questions: Sequence[
        Question
    ] = await questions_repo.questions.get_available_to_return_questions()
    active_questions = await questions_repo.questions.get_active_questions()

    if (
        question.status == "closed"
        and question.employee_fullname
        not in [u.employee_fullname for u in active_questions]
        and question.token in [d.token for d in available_to_return_questions]
        and question.topic_duty_fullname == user.FIO
    ):
        await questions_repo.questions.update_question_status(
            token=question.token, status="open"
        )

        await callback.bot.edit_forum_topic(
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
            message_thread_id=question.topic_id,
            name=f"{user.Division} | {user.FIO}"
            if "НТП" in user.Division
            else user.FIO,
            icon_custom_emoji_id=dicts.topicEmojis["in_progress"],
        )
        await callback.bot.reopen_forum_topic(
            chat_id=config.tg_bot.ntp_forum_id
            if "НТП" in user.Division
            else config.tg_bot.nck_forum_id,
            message_thread_id=question.topic_id,
        )

        await callback.message.answer("""<b>🔓 Вопрос переоткрыт</b>

Можешь писать сообщения, они будут переданы специалисту""")
        await callback.bot.send_message(
            chat_id=question.employee_chat_id,
            text=f"""<b>🔓 Вопрос переоткрыт</b>

Дежурный <b>{user.FIO}</b> переоткрыл вопрос:
<blockquote expandable><i>{question.question_text}</i></blockquote>""",
            reply_markup=finish_question_kb(),
        )
        logger.info(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Вопрос {question.token} переоткрыт старшим"
        )
    elif question.topic_duty_fullname != user.FIO:
        await callback.answer("Это не твой чат!", show_alert=True)
        logger.warning(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия, вопрос {question.token} принадлежит другому старшему"
        )
    elif question.employee_fullname in [d.employee_fullname for d in active_questions]:
        await callback.answer(
            "У специалиста есть другой открытый вопрос", show_alert=True
        )
        logger.error(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия, у специалиста {question.employee_fullname} есть другой открытый вопрос"
        )
    elif question.token not in [d.token for d in available_to_return_questions]:
        await callback.answer(
            "Вопрос не переоткрыть. Прошло более 24 часов или возврат заблокирован",
            show_alert=True,
        )
        logger.error(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия, диалог {question.token} был закрыт более 24 часов назад или возврат заблокирован"
        )
    elif question.status != "closed":
        await callback.answer("Этот вопрос не закрыт", show_alert=True)
        logger.error(
            f"[Вопрос] - [Переоткрытие] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка переоткрытия, диалог {question.token} не закрыт"
        )

    await callback.answer()


@topic_router.callback_query(IsTopicMessage() and QuestionAllowReturn.filter())
async def change_q_return_status(
    callback: CallbackQuery,
    callback_data: QuestionQualityDuty,
    question: Question,
    questions_repo: RequestsRepo,
):
    await questions_repo.questions.update_question_return_status(
        token=callback_data.token, status=callback_data.allow_return
    )
    if callback_data.allow_return:
        await callback.answer("🟢 Возврат текущего вопроса был разрешен")
    else:
        await callback.answer("⛔ Возврат текущего вопроса был разрешен")

    await callback.message.edit_reply_markup(
        reply_markup=question_quality_duty_kb(
            token=callback_data.token,
            show_quality=True if question.quality_duty is None else None,
            allow_return=callback_data.allow_return,
        )
    )
    await callback.answer()


@topic_router.callback_query(IsTopicMessage() and QuestionQualityDuty.filter())
async def quality_q_duty(
    callback: CallbackQuery,
    callback_data: QuestionQualityDuty,
    user: User,
    questions_repo: RequestsRepo,
    question: Question,
):
    if question.topic_duty_fullname == user.FIO:
        await questions_repo.questions.update_question_quality(
            token=callback_data.token, quality=callback_data.answer, is_duty=True
        )
        await callback.answer("Оценка успешно выставлена ❤️")
        if callback_data.answer:
            await callback.message.edit_text(
                f"""<b>🔒 Вопрос закрыт</b>

👮‍♂️ Дежурный <b>{user.FIO}</b> поставил оценку:
👎 Специалист <b>мог решить вопрос самостоятельно</b>""",
                reply_markup=closed_question_duty_kb(
                    token=callback_data.token,
                ),
            )
        else:
            await callback.message.edit_text(
                f"""<b>🔒 Вопрос закрыт</b>

👮‍♂️ Дежурный <b>{user.FIO}</b> поставил оценку:
👍 Специалист <b>не мог решить вопрос самостоятельно</b>""",
                reply_markup=closed_question_duty_kb(token=callback_data.token),
            )

        logger.info(
            f"[Вопрос] - [Оценка] Пользователь {callback.from_user.username} ({callback.from_user.id}): Выставлена оценка {callback_data.answer} вопросу {question.token} от старшего"
        )
    else:
        await callback.answer("Это не твой чат!", show_alert=True)
        logger.warning(
            f"[Вопрос] - [Оценка] Пользователь {callback.from_user.username} ({callback.from_user.id}): Неудачная попытка выставить оценку {callback_data.answer} вопросу {question.token}. Вопрос принадлежит другому старшему"
        )
    await callback.answer()
