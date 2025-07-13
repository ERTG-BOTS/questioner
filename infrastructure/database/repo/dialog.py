from datetime import datetime, date
from typing import Optional, Sequence
import uuid

from sqlalchemy import select

from infrastructure.database.models import Dialog
from infrastructure.database.repo.base import BaseRepo


class DialogHistoriesRepo(BaseRepo):
    async def add_dialog(
            self, employee_chat_id: int, employee_fullname: str, topic_id: int,
            question: str, start_time: date, clever_link: str
    ) -> Dialog:
        """
        Добавляет новый диалог в базу данных.

        Args:
            employee_chat_id (int): Chat ID сотрудника, задающего вопрос
            employee_fullname (str): ФИО сотрудника, задающего вопрос
            topic_id (int): ID топика
            topic_duty (str): Описание обязанности топика
            question (str): Вопрос диалога
            start_time (date): Дата начала диалога
            clever_link (str): Ссылка на clever

        Returns:
            Dialog: Созданный объект диалога
        """
        # Генерируем уникальный токен для диалога
        token = str(uuid.uuid4())

        # Создаем новый объект Dialog
        dialog = Dialog(
            Token=token,
            TopicId=topic_id,
            EmployeeFullname=employee_fullname,
            EmployeeChatId=employee_chat_id,
            Question=question,
            StartTime=start_time,
            CleverLink=clever_link
        )

        # Добавляем в сессию и сохраняем
        self.session.add(dialog)
        await self.session.commit()
        await self.session.refresh(dialog)

        return dialog

    async def update_dialog_end(self, token: str, end_time: date) -> Optional[Dialog]:
        """
        Обновляет дату окончания диалога.

        Args:
            token (str): Токен диалога
            end_time (date): Дата окончания диалога

        Returns:
            Dialog: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(Dialog, token)
        if dialog:
            dialog.EndTime = end_time
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def update_dialog_quality(self, token: str, quality: bool, is_duty: bool = False) -> Optional[Dialog]:
        """
        Обновляет качество диалога.

        Args:
            token (str): Токен диалога
            quality (bool): Оценка качества
            is_duty (bool): Флаг, указывающий на оценку дежурного

        Returns:
            Dialog: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(Dialog, token)
        if dialog:
            if is_duty:
                dialog.DialogQualityDuty = quality
            else:
                dialog.DialogQualityEmployee = quality
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def update_question(self, token: str, question: str) -> Optional[Dialog]:
        """
        Обновляет вопрос диалога.

        Args:
            token (str): Токен диалога
            question (str): Вопрос

        Returns:
            Dialog: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(Dialog, token)
        if dialog:
            dialog.Question = question
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def update_topic_duty(self, token: str, topic_duty: str) -> Optional[Dialog]:
        """
        Обновляет описание обязанности топика.

        Args:
            token (str): Токен диалога
            topic_duty (str): Описание обязанности топика

        Returns:
            Dialog: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(Dialog, token)
        if dialog:
            dialog.TopicDuty = topic_duty
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def get_dialog_by_topic_id(self, topic_id: int) -> Optional[Dialog]:
        """
        Получает диалог по идентификатору топика.

        Args:
            topic_id (int): ID топика

        Returns:
            Dialog: Диалог или None если не найден
        """
        stmt = select(Dialog).where(Dialog.TopicId == topic_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_dialogs_by_employee(self, employee_fullname: str) -> Sequence[Dialog]:
        """
        Получает все диалоги сотрудника.

        Args:
            employee_fullname (str): ФИО сотрудника

        Returns:
            Sequence[Dialog]: Список диалогов сотрудника
        """
        stmt = select(Dialog).where(Dialog.EmployeeFullname == employee_fullname)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_dialogs_by_employee_chat_id(self, employee_chat_id: int) -> Sequence[Dialog]:
        """
        Получает все диалоги сотрудника по Chat ID.

        Args:
            employee_chat_id (int): Chat ID сотрудника

        Returns:
            Sequence[Dialog]: Список диалогов сотрудника
        """
        stmt = select(Dialog).where(Dialog.EmployeeChatId == employee_chat_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_dialogs_by_topic_duty(self, topic_duty: str) -> Sequence[Dialog]:
        """
        Получает все диалоги по описанию обязанности топика.

        Args:
            topic_duty (str): Описание обязанности топика

        Returns:
            Sequence[Dialog]: Список диалогов
        """
        stmt = select(Dialog).where(Dialog.TopicDuty == topic_duty)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_dialogs_with_quality_rating(self, is_duty: bool = False) -> Sequence[Dialog]:
        """
        Получает все диалоги с оценкой качества.

        Args:
            is_duty (bool): Если True, возвращает диалоги с оценкой дежурного

        Returns:
            Sequence[Dialog]: Список диалогов с оценкой
        """
        if is_duty:
            stmt = select(Dialog).where(Dialog.DialogQualityDuty.is_not(None))
        else:
            stmt = select(Dialog).where(Dialog.DialogQualityEmployee.is_not(None))

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_dialogs_by_date_range(self, start_date: date, end_date: date) -> Sequence[Dialog]:
        """
        Получает диалоги в указанном диапазоне дат.

        Args:
            start_date (date): Начальная дата
            end_date (date): Конечная дата

        Returns:
            Sequence[Dialog]: Список диалогов в диапазоне дат
        """
        stmt = select(Dialog).where(
            Dialog.StartTime >= start_date,
            Dialog.StartTime <= end_date
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_dialogs(self) -> Sequence[Dialog]:
        """
        Получает все активные диалоги (без даты окончания).

        Returns:
            Sequence[Dialog]: Список активных диалогов
        """
        stmt = select(Dialog).where(Dialog.EndTime.is_(None))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_completed_dialogs(self) -> Sequence[Dialog]:
        """
        Получает все завершенные диалоги (с датой окончания).

        Returns:
            Sequence[Dialog]: Список завершенных диалогов
        """
        stmt = select(Dialog).where(Dialog.EndTime.is_not(None))
        result = await self.session.execute(stmt)
        return result.scalars().all()