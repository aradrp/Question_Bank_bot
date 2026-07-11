"""
keyboards/admin_keyboard.py – Persistent reply keyboard shown to admins.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Human-readable button labels
BTN_ADD_SUBJECT  = "➕ Add Subject"
BTN_ADD_CHAPTER  = "➕ Add Chapter"
BTN_ADD_TOPIC    = "➕ Add Topic"
BTN_UPLOAD       = "📤 Upload Question"
BTN_DELETE       = "🗑 Delete Question"
BTN_LIST         = "📋 List Questions"
BTN_STATS        = "📊 Statistics"
BTN_BUILD_ZIP    = "📦 Build ZIP Package"


def admin_main_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BTN_ADD_SUBJECT), KeyboardButton(text=BTN_ADD_CHAPTER))
    builder.row(KeyboardButton(text=BTN_ADD_TOPIC),   KeyboardButton(text=BTN_UPLOAD))
    builder.row(KeyboardButton(text=BTN_DELETE),      KeyboardButton(text=BTN_LIST))
    builder.row(KeyboardButton(text=BTN_STATS),       KeyboardButton(text=BTN_BUILD_ZIP))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)
