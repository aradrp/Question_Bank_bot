"""
filters/admin_filter.py – Aiogram filter that allows only whitelisted admins.

Admin IDs come from the Config object injected by the dispatcher.
"""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import Config


class AdminFilter(BaseFilter):
    """Pass only if the Telegram user ID appears in Config.ADMIN_IDS."""

    async def __call__(  # type: ignore[override]
        self,
        event: Message | CallbackQuery,
        config: Config,
    ) -> bool:
        user_id: int | None = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id if event.from_user else None
        return user_id is not None and user_id in config.ADMIN_IDS
