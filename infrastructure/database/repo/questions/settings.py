import json
import logging
from typing import Any, Dict, Optional, Sequence, TypedDict

from sqlalchemy import func, select

from infrastructure.database.models.questions.settings import Settings
from infrastructure.database.repo.base import BaseRepo
from tgbot.services.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class SettingsUpdateParams(TypedDict, total=False):
    """Доступные параметры для обновления настроек."""

    group_id: int
    values: str
    last_update: str


class SettingsRepo(BaseRepo):
    async def add_settings(
        self,
        group_id: int,
        values: Optional[Dict[str, Any]] = None,
    ) -> Settings:
        """
        Добавление новых настроек для группы
        :param group_id: ID группы Telegram
        :param values: Словарь с настройками (по умолчанию пустой)
        :return: Созданный объект Settings
        """
        if values is None:
            values = {}

        settings = Settings(
            group_id=group_id,
            values=json.dumps(values, ensure_ascii=False),
        )

        self.session.add(settings)
        await self.session.commit()
        await self.session.refresh(settings)

        logger.info(f"Settings created for group {group_id}")
        return settings

    async def get_settings_by_group_id(self, group_id: int) -> Optional[Settings]:
        """
        Получение настроек по ID группы
        :param group_id: ID группы Telegram
        :return: Объект Settings или None, если не найден
        """
        stmt = select(Settings).where(Settings.group_id == group_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_settings_by_id(self, settings_id: int) -> Optional[Settings]:
        """
        Получение настроек по ID записи
        :param settings_id: ID записи настроек
        :return: Объект Settings или None, если не найден
        """
        return await self.session.get(Settings, settings_id)

    async def get_all_settings(self) -> Sequence[Settings]:
        """
        Получение всех настроек
        :return: Список всех настроек
        """
        stmt = select(Settings).order_by(Settings.last_update.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_settings(
        self, group_id: int, values: Dict[str, Any]
    ) -> Optional[Settings]:
        """
        Обновление настроек группы
        :param group_id: ID группы Telegram
        :param values: Новые значения настроек
        :return: Обновленный объект Settings или None, если не найден
        """
        settings = await self.get_settings_by_group_id(group_id)
        if settings is None:
            return None

        settings.set_values(values)
        settings.last_update = func.now()

        await self.session.commit()
        await self.session.refresh(settings)

        logger.info(f"[Настройки] Изменены настройки для группы {group_id}")
        return settings

    async def update_setting(
        self, group_id: int, key: str, value: Any
    ) -> Optional[Settings]:
        """
        Обновление конкретной настройки
        :param group_id: ID группы Telegram
        :param key: Ключ настройки
        :param value: Новое значение
        :return: Обновленный объект Settings или None, если не найден
        """
        settings = await self.get_settings_by_group_id(group_id)
        if settings is None:
            return None

        settings.set_setting(key, value)
        settings.last_update = func.now()

        await self.session.commit()
        await self.session.refresh(settings)

        logger.info(f"Setting '{key}' updated for group {group_id}")
        return settings

    async def get_or_create_settings(
        self, group_id: int, default_values: Optional[Dict[str, Any]] = None
    ) -> Settings:
        """
        Получение настроек или создание новых, если не существуют
        :param group_id: ID группы Telegram
        :param default_values: Значения по умолчанию для новых настроек
        :return: Объект Settings
        """
        settings = await self.get_settings_by_group_id(group_id)
        if settings is None:
            if default_values is None:
                default_values = {
                    "ask_clever_link": True,
                    "activity_status": True,
                    "activity_warn_minutes": 5,
                    "activity_close_minutes": 10,
                }
            settings = await self.add_settings(group_id, default_values)

        return settings

    async def delete_settings(self, group_id: int) -> dict:
        """
        Удаление настроек группы
        :param group_id: ID группы Telegram
        :return: Словарь с результатом удаления
        """
        try:
            settings = await self.get_settings_by_group_id(group_id)
            if settings is None:
                return {
                    "success": False,
                    "deleted_count": 0,
                    "errors": [f"Settings for group {group_id} not found"],
                }

            await self.session.delete(settings)
            await self.session.commit()

            logger.info(f"Settings deleted for group {group_id}")
            return {
                "success": True,
                "deleted_count": 1,
                "errors": [],
            }

        except Exception as e:
            await self.session.rollback()
            error_msg = f"Database error: {str(e)}"
            logger.error(f"Error deleting settings for group {group_id}: {error_msg}")
            return {
                "success": False,
                "deleted_count": 0,
                "errors": [error_msg],
            }

    async def get_settings_with_value(self, key: str, value: Any) -> Sequence[Settings]:
        """
        Получение всех настроек, где конкретный ключ имеет определенное значение
        :param key: Ключ настройки
        :param value: Искомое значение
        :return: Список Settings
        """
        all_settings = await self.get_all_settings()
        filtered_settings = []

        for settings in all_settings:
            if settings.get_setting(key) == value:
                filtered_settings.append(settings)

        return filtered_settings

    async def bulk_update_setting(
        self, group_ids: Sequence[int], key: str, value: Any
    ) -> dict:
        """
        Массовое обновление настройки для нескольких групп
        :param group_ids: Список ID групп
        :param key: Ключ настройки
        :param value: Новое значение
        :return: Словарь с результатом операции
        """
        updated_count = 0
        errors = []

        try:
            for group_id in group_ids:
                try:
                    result = await self.update_setting(group_id, key, value)
                    if result:
                        updated_count += 1
                    else:
                        errors.append(f"Settings for group {group_id} not found")
                except Exception as e:
                    errors.append(f"Error updating group {group_id}: {str(e)}")

            return {
                "success": updated_count > 0,
                "updated_count": updated_count,
                "total_count": len(group_ids),
                "errors": errors,
            }

        except Exception as e:
            await self.session.rollback()
            error_msg = f"Database error: {str(e)}"
            logger.error(f"Error in bulk update: {error_msg}")
            return {
                "success": False,
                "updated_count": updated_count,
                "total_count": len(group_ids),
                "errors": [error_msg],
            }
