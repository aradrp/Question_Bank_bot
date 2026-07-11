"""
keyboards/user_keyboard.py – User-facing keyboards.
Primary navigation is inline; this module is a placeholder for any
future reply-keyboard needs.
"""
from aiogram.types import ReplyKeyboardRemove

def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
