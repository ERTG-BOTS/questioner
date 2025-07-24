import uuid
from datetime import date, datetime, timedelta
from typing import Optional, Sequence

from sqlalchemy import Row, and_, extract, func, or_, select

from infrastructure.database.models import Question
from infrastructure.database.repo.base import BaseRepo
from tgbot.config import load_config

config = load_config(".env")


class QuestionsRepo(BaseRepo):
    async def add_question(
        self,
        employee_chat_id: int,
        employee_fullname: str,
        topic_id: int,
        question_text: str,
        start_time: date,
        clever_link: str,
        activity_status_enabled: Optional[bool] = None,
    ) -> Question:
        """
        Добавление нового вопроса
        :param employee_chat_id: Идентификатор Telegram специалиста, задавшего вопроса
        :param employee_fullname: ФИО специалиста, задавшего вопроса
        :param topic_id: Идентификатор топика Telegram, в котором вопрос решается
        :param question_text: Текст заданного вопроса
        :param start_time: Время открытия вопроса
        :param clever_link: Ссылка на базу знаний от специалиста
        :param activity_status_enabled: Включено ли отслеживание бездействия
        :return: Объект созданного вопроса
        """
        token = str(uuid.uuid4())

        question = Question(
            token=token,
            topic_id=topic_id,
            employee_fullname=employee_fullname,
            employee_chat_id=employee_chat_id,
            question_text=question_text,
            start_time=start_time,
            clever_link=clever_link,
            status="open",
            allow_return=True,
            activity_status_enabled=activity_status_enabled,
        )

        self.session.add(question)
        await self.session.commit()
        await self.session.refresh(question)
        return question

    async def get_question(
        self, token: str = None, topic_id: int = None
    ) -> Optional[Question]:
        """
        Получение вопроса по токену или идентификатору топика
        :param token: Уникальный токен вопроса
        :param topic_id: Идентификатор топика в Telegram
        :return: Найденный вопрос или None
        """
        if token:
            stmt = select(Question).where(Question.token == token)
        else:
            stmt = select(Question).where(Question.topic_id == topic_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_questions(self) -> Sequence[Question]:
        """
        Получение текущих активных вопросов. Активным вопросом считается вопрос, имеющий статус open или in_progress
        :return: Последовательность активных вопросов
        """
        stmt = select(Question).where(
            or_(Question.status == "open", Question.status == "in_progress")
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_question_status(
        self, token: str, status: str
    ) -> Optional[Question]:
        """
        Обновление статуса вопроса
        :param token: Уникальный идентификатор вопроса
        :param status: Новый статус
        :return: Обновленный объект вопроса
        """
        question = await self.session.get(Question, token)
        if question:
            question.status = status
            await self.session.commit()
            await self.session.refresh(question)
        return question

    async def update_question_end(
        self, token: str, end_time: date
    ) -> Optional[Question]:
        """
        Обновление времени закрытия вопроса
        :param token: Уникальный идентификатор вопроса
        :param end_time: Время закрытия вопроса
        :return: Обновленный объект вопроса
        """
        question = await self.session.get(Question, token)
        if question:
            question.end_time = end_time
            await self.session.commit()
            await self.session.refresh(question)
        return question

    async def update_question_quality(
        self, token: str, quality: bool, is_duty: bool = False
    ) -> Optional[Question]:
        """
        Обновление оценки вопроса. Может быть использовано и дежурным, и специалистом
        :param token: Уникальный идентификатор вопроса
        :param quality: Выставляемое качество
        :param is_duty: Оценка от дежурного или нет
        :return: Обновленный объект вопроса
        """
        question = await self.session.get(Question, token)
        if question:
            if is_duty:
                question.quality_duty = quality
            else:
                question.quality_employee = quality
            await self.session.commit()
            await self.session.refresh(question)
        return question

    async def update_question_duty(
        self, token: str, topic_duty: Optional[str]
    ) -> Optional[Question]:
        """
        Обновление дежурного, ответственного за вопрос
        :param token: Уникальный идентификатор вопроса
        :param topic_duty: Дежурный, закрепляемый за вопросом
        :return: Обновленный объект вопроса
        """
        question = await self.session.get(Question, token)
        if question:
            question.topic_duty_fullname = topic_duty
            await self.session.commit()
            await self.session.refresh(question)
        return question

    async def update_question_return_status(
        self, token: str, status: bool
    ) -> Optional[Question]:
        """
        Обновление статуса возможности возврата вопроса
        :param token: Уникальный идентификатор вопроса
        :param status: Новый статус возможности возврата
        :return: Обновленный объект вопроса
        """
        question = await self.session.get(Question, token)
        if question:
            question.allow_return = status
            await self.session.commit()
            await self.session.refresh(question)
        return question

    async def update_question_activity_status(
        self, token: str, activity_status_enabled: Optional[bool]
    ) -> Optional[Question]:
        """
        Обновление статуса отслеживания бездействия
        :param token: Уникальный идентификатор вопроса
        :param activity_status_enabled: Новый статус отслеживания бездействия
        :return: Обновленный объект вопроса
        """
        question = await self.session.get(Question, token)
        if question:
            question.activity_status_enabled = activity_status_enabled
            await self.session.commit()
            await self.session.refresh(question)
        return question

    # TODO Добавить фильтр по направлению специалиста
    async def get_questions_by_month(
        self, month: int, year: int, division: str = None
    ) -> Sequence[Row[tuple[Question]]]:
        """
        Получение вопросов за конкретный месяц
        :param month: Фильтр по месяцу
        :param year: Фильтр по году
        :param division: Фильтр по направлению
        :return: Последовательность вопросов, подходящих под фильтры
        """
        stmt = select(Question).where(
            extract("month", Question.start_time) == month,
            extract("year", Question.start_time) == year,
        )

        result = await self.session.execute(stmt)
        return result.fetchall()

    async def get_questions_count_today(
        self, employee_fullname: str = None, duty_fullname: str = None
    ) -> int:
        """
        Получение кол-ва вопросов специалиста за последний день. Может использоваться как для поиска вопросов специалиста, так и для вопросов дежурного
        :param employee_fullname: ФИО искомого специалиста
        :param duty_fullname: ФИО искомого дежурного
        :return: Кол-во вопросов за последний день
        """
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        if employee_fullname:
            stmt = select(func.count(Question.token)).where(
                and_(
                    Question.employee_fullname == employee_fullname,
                    Question.start_time >= today,
                    Question.start_time < tomorrow,
                )
            )
        else:
            stmt = select(func.count(Question.token)).where(
                and_(
                    Question.topic_duty_fullname == duty_fullname,
                    Question.start_time >= today,
                    Question.start_time < tomorrow,
                )
            )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_questions_count_last_month(
        self, employee_fullname: str = None, duty_fullname: str = None
    ) -> int:
        """
        Получение кол-ва вопросов специалиста за последний месяц. Может использоваться как для поиска вопросов специалиста, так и для вопросов дежурного
        :param employee_fullname: ФИО искомого специалиста
        :param duty_fullname: ФИО искомого дежурного
        :return: Кол-во вопросов за последний месяц
        """
        today = datetime.now()
        first_day_current_month = datetime(today.year, today.month, 1).date()

        if today.month == 12:
            next_month = 1
            next_year = today.year + 1
        else:
            next_month = today.month + 1
            next_year = today.year

        first_day_next_month = datetime(next_year, next_month, 1).date()

        if employee_fullname:
            stmt = select(func.count(Question.token)).where(
                and_(
                    Question.employee_fullname == employee_fullname,
                    Question.start_time >= first_day_current_month,
                    Question.start_time < first_day_next_month,
                )
            )
        else:
            stmt = select(func.count(Question.token)).where(
                and_(
                    Question.topic_duty_fullname == duty_fullname,
                    Question.start_time >= first_day_current_month,
                    Question.start_time < first_day_next_month,
                )
            )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_last_questions_by_chat_id(
        self, employee_chat_id: int, limit: int = 5
    ) -> Sequence[Question]:
        """
        Получение последних N вопросов специалиста
        :param employee_chat_id: Идентификатор специалиста Telegram
        :param limit: Лимит вопросов для выдачи. Сортировка по убыванию даты закрытия вопроса
        :return: Последовательность вопросов
        """
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)

        stmt = (
            select(Question)
            .where(
                and_(
                    Question.employee_chat_id == employee_chat_id,
                    Question.question_text.is_not(None),
                    Question.status == "closed",
                    Question.end_time.is_not(None),
                    Question.end_time >= twenty_four_hours_ago,
                    Question.allow_return,
                )
            )
            .order_by(Question.end_time.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_available_to_return_questions(self) -> Sequence[Question]:
        """
        Получение всех доступных к возврату вопросов
        :return: Последовательность доступных к возврату вопросов
        """
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)

        stmt = (
            select(Question)
            .where(
                and_(
                    Question.question_text.is_not(None),
                    Question.status == "closed",
                    Question.end_time.is_not(None),
                    Question.end_time >= twenty_four_hours_ago,
                    Question.allow_return,
                )
            )
            .order_by(Question.end_time.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_old_questions(self) -> Sequence[Question]:
        """
        Получение вопросов старше выставленной в конфиге даты
        :return: Последовательность вопросов старше определенной даты
        """
        today = datetime.now()
        old_date = today - timedelta(days=config.tg_bot.remove_old_questions_days)

        stmt = select(Question).where(Question.start_time < old_date)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_question(
        self, token: str = None, questions: Sequence[Question] = None
    ) -> dict:
        """
        Удаление вопроса из БД. Удаляет либо вопрос по его токену, либо список вопросов, переданный в questions
        :param token: Уникальный идентификатор вопроса
        :param questions: Последовательность вопросов на удаление
        :return: Словарь с результатом удаления
        """
        if token is None and questions is None:
            return {
                "success": False,
                "deleted_count": 0,
                "total_count": 0,
                "errors": ["Either token or questions must be provided"],
            }

        deleted_count = 0
        errors = []

        try:
            if token:
                question = await self.session.get(Question, token)
                if question is None:
                    return {
                        "success": False,
                        "deleted_count": 0,
                        "total_count": 1,
                        "errors": [f"Question with token {token} not found"],
                    }
                await self.session.delete(question)
                deleted_count = 1
                total_count = 1
            else:
                total_count = len(questions)
                for question in questions:
                    try:
                        await self.session.refresh(question)
                        await self.session.delete(question)
                        deleted_count += 1
                    except Exception as e:
                        errors.append(
                            f"Error deleting question {question.token}: {str(e)}"
                        )

            await self.session.commit()

            return {
                "success": deleted_count > 0,
                "deleted_count": deleted_count,
                "total_count": total_count,
                "errors": errors,
            }

        except Exception as e:
            await self.session.rollback()
            errors.append(f"Database error: {str(e)}")
            return {
                "success": False,
                "deleted_count": deleted_count,
                "total_count": total_count if "total_count" in locals() else 0,
                "errors": errors,
            }
