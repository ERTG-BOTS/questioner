import uuid
from datetime import datetime, date, timedelta
from typing import Optional, Sequence

from sqlalchemy import select, func, and_, or_

from infrastructure.database.models.question import Question
from infrastructure.database.repo.base import BaseRepo


class QuestionsRepo(BaseRepo):
    async def add_question(
            self, employee_chat_id: int, employee_fullname: str, topic_id: int,
            question_text: str, start_time: date, clever_link: str
    ) -> Question:
        """
        Добавляет новый диалог в базу данных.

        Args:
            employee_chat_id (int): Chat ID сотрудника, задающего вопрос
            employee_fullname (str): ФИО сотрудника, задающего вопрос
            topic_id (int): ID топика
            question_text (str): Вопрос диалога
            start_time (date): Дата начала диалога
            clever_link (str): Ссылка на clever

        Returns:
            Question: Созданный объект диалога
        """
        # Генерируем уникальный токен для диалога
        token = str(uuid.uuid4())

        # Создаем новый объект Question
        dialog = Question(
            Token=token,
            TopicId=topic_id,
            EmployeeFullname=employee_fullname,
            EmployeeChatId=employee_chat_id,
            QuestionText=question_text,
            StartTime=start_time,
            CleverLink=clever_link,
            Status="new",
        )

        self.session.add(dialog)
        await self.session.commit()
        await self.session.refresh(dialog)

        return dialog

    async def update_question_end(self, token: str, end_time: date) -> Optional[Question]:
        """
        Обновляет дату окончания диалога.

        Args:
            token (str): Токен диалога
            end_time (date): Дата окончания диалога

        Returns:
            Question: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(Question, token)
        if dialog:
            dialog.EndTime = end_time
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def update_question_quality(self, token: str, quality: bool, is_duty: bool = False) -> Optional[Question]:
        """
        Обновляет качество диалога.

        Args:
            token (str): Токен диалога
            quality (bool): Оценка качества
            is_duty (bool): Флаг, указывающий на оценку дежурного

        Returns:
            Question: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(Question, token)
        if dialog:
            if is_duty:
                dialog.QualityDuty = quality
            else:
                dialog.QualityEmployee = quality
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def update_question_status(self, token: str, status: str) -> Optional[Question]:
        """
        Обновляет качество диалога.

        Args:
            token (str): Токен диалога
            status (str): Статус вопроса

        Returns:
            Question: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(Question, token)
        if dialog:
            dialog.Status = status
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def update_question_duty(self, token: str, topic_duty: Optional[str]) -> Optional[Question]:
        """
        Обновляет описание обязанности топика.

        Args:
            token (str): Токен диалога
            topic_duty (str): Описание обязанности топика

        Returns:
            Question: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(Question, token)
        if dialog:
            dialog.TopicDutyFullname = topic_duty
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def get_question(self, token: str = None, topic_id: int = None) -> Optional[Question]:
        """
        Получает диалог по токену или идентификатору топика.

        Args:
            token (str): Токен топика
            topic_id (int): ID топика

        Returns:
            Question: Диалог или None если не найден
        """
        if token:
            stmt = select(Question).where(Question.Token == token)
        else:
            stmt = select(Question).where(Question.TopicId == topic_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_questions_by_fullname(self, employee_fullname: str = None, duty_fullname: str = None) -> Sequence[
        Question]:
        """
        Получает все диалоги сотрудника или старшего по ФИО.

        Args:
            employee_fullname (str): ФИО сотрудника
            duty_fullname (str): ФИО старшего

        Returns:
            Sequence[Question]: Список диалогов сотрудника
        """
        if employee_fullname:
            stmt = select(Question).where(Question.EmployeeFullname == employee_fullname)
        else:
            stmt = select(Question).where(Question.TopicDutyFullname == duty_fullname)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_questions_count_today(self, employee_fullname: str = None, duty_fullname: str = None) -> int:
        """
        Получает количество диалогов специалиста или старшего за сегодня.

        Args:
            employee_fullname (str): ФИО специалиста
            duty_fullname (str): ФИО старшего

        Returns:
            int: Количество диалогов за сегодня
        """
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        if employee_fullname:
            stmt = select(func.count(Question.Token)).where(
                and_(
                    Question.EmployeeFullname == employee_fullname,
                    Question.StartTime >= today,
                    Question.StartTime < tomorrow
                )
            )
        else:
            stmt = select(func.count(Question.Token)).where(
                and_(
                    Question.TopicDutyFullname == duty_fullname,
                    Question.StartTime >= today,
                    Question.StartTime < tomorrow
                )
            )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_questions_count_last_month(self, employee_fullname: str = None, duty_fullname: str = None) -> int:
        """
        Получает количество диалогов специалиста или старшего за текущий месяц.

        Args:
            employee_fullname (str): ФИО специалиста
            duty_fullname (str): ФИО старшего

        Returns:
            int: Количество диалогов за текущий месяц
        """
        today = datetime.now()
        # Получаем первый день текущего месяца
        first_day_current_month = datetime(today.year, today.month, 1).date()

        # Получаем первый день следующего месяца
        if today.month == 12:
            next_month = 1
            next_year = today.year + 1
        else:
            next_month = today.month + 1
            next_year = today.year

        first_day_next_month = datetime(next_year, next_month, 1).date()

        if employee_fullname:
            stmt = select(func.count(Question.Token)).where(
                and_(
                    Question.EmployeeFullname == employee_fullname,
                    Question.StartTime >= first_day_current_month,
                    Question.StartTime < first_day_next_month
                )
            )
        else:
            stmt = select(func.count(Question.Token)).where(
                and_(
                    Question.TopicDutyFullname == duty_fullname,
                    Question.StartTime >= first_day_current_month,
                    Question.StartTime < first_day_next_month
                )
            )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_questions_by_employee_chat_id(self, employee_chat_id: int) -> Sequence[Question]:
        """
        Получает все диалоги сотрудника по Chat ID.

        Args:
            employee_chat_id (int): Chat ID сотрудника

        Returns:
            Sequence[Question]: Список диалогов сотрудника
        """
        stmt = select(Question).where(Question.EmployeeChatId == employee_chat_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_questions(self) -> Sequence[Question]:
        """
        Получает все активные диалоги (со статусов open или in_progress).

        Returns:
            Sequence[Question]: Список активных диалогов
        """
        stmt = select(Question).where(
            or_(Question.Status == "open", Question.Status == "in_progress")
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_old_questions(self) -> Sequence[Question]:
        """
        Получает диалоги старше 2 месяцев.

        Returns:
            Sequence[Dialog]: Список диалогов старше 2 месяцев
        """
        from datetime import datetime, timedelta

        # Считаем дату два месяца назад
        today = datetime.now()
        two_months_ago = today - timedelta(days=1)  # Примерно 2 месяца

        stmt = select(Question).where(Question.StartTime < two_months_ago)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_last_questions_by_chat_id(self, employee_chat_id: int, limit: int = 5) -> Sequence[Question]:
        """
        Получает последние N закрытых вопросов пользователя за последние 24 часа по Chat ID, отсортированные по дате окончания.

        Args:
            employee_chat_id (int): Chat ID сотрудника
            limit (int): Количество вопросов для получения (по умолчанию 5)

        Returns:
            Sequence[Question]: Список последних закрытых вопросов пользователя за 24 часа
        """
        # Вычисляем время 24 часа назад
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        
        stmt = select(Question).where(
            and_(
                Question.EmployeeChatId == employee_chat_id,
                Question.QuestionText != None,
                Question.Status == "closed",
                Question.EndTime.is_not(None),
                Question.EndTime < twenty_four_hours_ago
            )
        ).order_by(Question.EndTime.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_question(self, token: str = None, dialogs: Sequence[Question] = None) -> dict:
        """
        Удаляет вопрос(ы) из базы данных по токену или последовательности вопросов.

        Args:
            token (str, optional): Токен вопроса для удаления
            dialogs (Sequence[Dialog], optional): Последовательность вопросов для удаления

        Returns:
            dict: Результат операции с ключами:
                - success (bool): True если операция выполнена успешно
                - deleted_count (int): Количество удаленных вопросов
                - total_count (int): Общее количество вопросов для удаления
                - errors (list): Список ошибок, если они возникли
        """
        if token is None and dialogs is None:
            return {
                "success": False,
                "deleted_count": 0,
                "total_count": 0,
                "errors": ["Either token or dialogs must be provided"]
            }

        if token is not None and dialogs is not None:
            return {
                "success": False,
                "deleted_count": 0,
                "total_count": 0,
                "errors": ["Cannot specify both token and dialogs"]
            }

        deleted_count = 0
        errors = []

        try:
            if token:
                # Single dialog deletion by token
                dialog = await self.session.get(Question, token)

                if dialog is None:
                    return {
                        "success": False,
                        "deleted_count": 0,
                        "total_count": 1,
                        "errors": [f"Dialog with token {token} not found"]
                    }

                await self.session.delete(dialog)
                deleted_count = 1
                total_count = 1

            else:
                # Multiple dialogs deletion
                total_count = len(dialogs)

                for dialog in dialogs:
                    try:
                        # Refresh the dialog object to ensure it's attached to the current session
                        await self.session.refresh(dialog)
                        await self.session.delete(dialog)
                        deleted_count += 1
                    except Exception as e:
                        errors.append(f"Error deleting dialog {dialog.Token}: {str(e)}")

            # Commit all deletions
            await self.session.commit()

            return {
                "success": deleted_count > 0,
                "deleted_count": deleted_count,
                "total_count": total_count,
                "errors": errors
            }

        except Exception as e:
            # Rollback in case of error
            await self.session.rollback()
            errors.append(f"Database error: {str(e)}")

            return {
                "success": False,
                "deleted_count": deleted_count,
                "total_count": total_count if 'total_count' in locals() else 0,
                "errors": errors
            }