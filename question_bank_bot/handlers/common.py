"""
handlers/common.py – Catch-all / error handlers.
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router()


@router.message()
async def unknown_message(message: Message) -> None:
    """Fallback for any unhandled message."""
    await message.answer(
        "❓ Unknown command.\n"
        "Use /start to browse questions, or /admin if you are an administrator."
    )
