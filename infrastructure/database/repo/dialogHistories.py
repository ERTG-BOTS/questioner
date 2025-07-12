from datetime import datetime
from typing import Optional, Sequence
import uuid

from sqlalchemy import select

from infrastructure.database.models import DialogHistory
from infrastructure.database.repo.base import BaseRepo


class DialogHistoriesRepo(BaseRepo):
    async def add_dialog(
            self, chat_id: int, fullname: str, start_message_id: int, message_thread_id: int, start_time: datetime, clever_link: str
    ) -> DialogHistory:
        """
        Добавляет новый диалог в базу данных.

        Args:
            chat_id (int): ID чата/потока сообщений
            fullname (str): ФИО сотрудника
            start_message_id (int): ID первого сообщения
            start_time (datetime): Время начала диалога
            clever_link (str): Ссылка или начальный вопрос

        Returns:
            DialogHistory: Созданный объект диалога
        """
        # Генерируем уникальный токен для диалога
        token = str(uuid.uuid4())

        # Создаем новый объект DialogHistory
        dialog = DialogHistory(
            Token=token,
            FIOEmployee=fullname,
            ListFIOSupervisor="",
            StartQuestion=start_time.strftime("%d.%m.%Y %H:%M:%S"),  # Время начала в формате дд.мм.гггг чч:мм:сс
            FirstMessageId=start_message_id,
            ListStartDialog=start_time.strftime("%d.%m.%Y %H:%M:%S"),  # Время начала диалога
            ListEndDialog="",  # Пустая строка, будет заполнена при завершении диалога
            DialogQuality=None,  # Качество будет оценено позже
            MessageThreadId=message_thread_id,
            DialogQualityRg=None,  # Качество от старшего будет оценено позже
            CleverLink=clever_link  # Добавляем поле CleverLink
        )

        # Добавляем в сессию и сохраняем
        self.session.add(dialog)
        await self.session.commit()
        await self.session.refresh(dialog)

        return dialog

    async def update_dialog_end(self, token: str, end_time: datetime) -> Optional[DialogHistory]:
        """
        Обновляет время окончания диалога.

        Args:
            token (str): Токен диалога
            end_time (datetime): Время окончания диалога

        Returns:
            DialogHistory: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(DialogHistory, token)
        if dialog:
            dialog.ListEndDialog = end_time.strftime("%d.%m.%Y %H:%M:%S")  # Формат дд.мм.гггг чч:мм:сс
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def update_dialog_quality(self, token: str, quality: bool, is_senior: bool = False) -> Optional[
        DialogHistory]:
        """
        Обновляет качество диалога.

        Args:
            token (str): Токен диалога
            quality (bool): Оценка качества
            is_senior (bool): Флаг, указывающий на оценку старшего

        Returns:
            DialogHistory: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(DialogHistory, token)
        if dialog:
            if is_senior:
                dialog.DialogQualityRg = quality
            else:
                dialog.DialogQuality = quality
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def update_start_question(self, token: str, start_question: str) -> Optional[DialogHistory]:
        """
        Обновляет начальный вопрос диалога.

        Args:
            token (str): Токен диалога
            start_question (str): Начальный вопрос

        Returns:
            DialogHistory: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(DialogHistory, token)
        if dialog:
            dialog.StartQuestion = start_question
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def update_supervisor(self, token: str, supervisor_name: str) -> Optional[DialogHistory]:
        """
        Обновляет руководителя диалога.

        Args:
            token (str): Токен диалога
            supervisor_name (str): ФИО руководителя

        Returns:
            DialogHistory: Обновленный объект диалога или None если не найден
        """
        dialog = await self.session.get(DialogHistory, token)
        if dialog:
            dialog.ListFIOSupervisor = supervisor_name
            await self.session.commit()
            await self.session.refresh(dialog)
        return dialog

    async def get_dialog_by_topic_id(self, topic_id: int) -> DialogHistory:
        """
        Получает диалог по идентификатору топика Telegram.

        Args:
            topic_id (int): ФИО сотрудника

        Returns:
            DialogHistory: Диалог со специалистом
        """
        from sqlalchemy import select

        stmt = select(DialogHistory).where(DialogHistory.MessageThreadId == topic_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_dialogs_by_employee(self, employee_name: str) -> Sequence[DialogHistory]:
        """
        Получает все диалоги сотрудника.

        Args:
            employee_name (str): ФИО сотрудника

        Returns:
            Sequence[DialogHistory]: Список диалогов сотрудника
        """
        from sqlalchemy import select

        stmt = select(DialogHistory).where(DialogHistory.FIOEmployee == employee_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_dialogs_by_supervisor(self, supervisor_name: str) -> Sequence[DialogHistory]:
        """
        Получает все диалоги под руководством указанного руководителя.

        Args:
            supervisor_name (str): ФИО руководителя

        Returns:
            Sequence[DialogHistory]: Список диалогов
        """
        from sqlalchemy import select

        stmt = select(DialogHistory).where(DialogHistory.ListFIOSupervisor == supervisor_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_dialogs_with_quality_rating(self, is_senior: bool = False) -> Sequence[DialogHistory]:
        """
        Получает все диалоги с оценкой качества.

        Args:
            is_senior (bool): Если True, возвращает диалоги с оценкой старшего

        Returns:
            Sequence[DialogHistory]: Список диалогов с оценкой
        """
        from sqlalchemy import select

        if is_senior:
            stmt = select(DialogHistory).where(DialogHistory.DialogQualityRg.is_not(None))
        else:
            stmt = select(DialogHistory).where(DialogHistory.DialogQuality.is_not(None))

        result = await self.session.execute(stmt)
        return result.scalars().all()