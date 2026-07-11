"""
handlers/start.py – /start command for all users.
handlers/common.py – Shared utility handlers (cancel, noop, back navigation).
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database.repository import Repository
from keyboards.admin_keyboard import admin_main_keyboard
from keyboards.inline_keyboard import (
    AdmCancelCD,
    BackCD,
    UsrNavCD,
    build_user_chapters_kb,
    build_user_subjects_kb,
    build_user_topics_kb,
)

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, config: Config, repo: Repository) -> None:
    user = message.from_user
    is_admin = user and user.id in config.ADMIN_IDS

    subjects = await repo.get_subjects_page(0, config.ITEMS_PER_PAGE)
    total = await repo.count_subjects()

    greeting = (
        f"👋 Welcome, <b>{user.first_name if user else 'User'}</b>!\n\n"
        "📚 <b>Question Bank Bot</b>\n"
        "Browse subjects below to find and download PDF questions.\n"
    )

    if is_admin:
        greeting += "\n🔑 <i>You have admin access.</i> Use the menu below to manage content."
        await message.answer(greeting, parse_mode="HTML", reply_markup=admin_main_keyboard())
    else:
        await message.answer(greeting, parse_mode="HTML")

    if not subjects:
        await message.answer("📭 No subjects available yet. Check back later!")
        return

    kb = build_user_subjects_kb(subjects, 0, total, config.ITEMS_PER_PAGE)
    await message.answer("📚 <b>Choose a subject:</b>", parse_mode="HTML", reply_markup=kb)


# ─────────────────────────────────────────────────────────────────────────────
# Shared: noop (page indicator buttons)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery) -> None:
    await cb.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Admin: cancel FSM
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(AdmCancelCD.filter())
async def cb_cancel(cb: CallbackQuery, state: FSMContext, config: Config) -> None:
    await state.clear()
    await cb.message.edit_text("❌ Action cancelled.")
    await cb.answer("Cancelled")


# ─────────────────────────────────────────────────────────────────────────────
# User: back navigation
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(BackCD.filter(F.to == "subj"))
async def cb_back_to_subjects(
    cb: CallbackQuery, config: Config, repo: Repository
) -> None:
    subjects = await repo.get_subjects_page(0, config.ITEMS_PER_PAGE)
    total = await repo.count_subjects()
    kb = build_user_subjects_kb(subjects, 0, total, config.ITEMS_PER_PAGE)
    await cb.message.edit_text("📚 <b>Choose a subject:</b>", parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@router.callback_query(BackCD.filter(F.to == "chap"))
async def cb_back_to_chapters(
    cb: CallbackQuery, callback_data: BackCD, config: Config, repo: Repository
) -> None:
    subject_id = callback_data.p1
    subject = await repo.get_subject(subject_id)
    if not subject:
        await cb.answer("Subject not found", show_alert=True)
        return
    chapters = await repo.get_chapters_page(subject_id, 0, config.ITEMS_PER_PAGE)
    total = await repo.count_chapters(subject_id)
    kb = build_user_chapters_kb(chapters, 0, total, config.ITEMS_PER_PAGE, subject_id)
    await cb.message.edit_text(
        f"📂 <b>{subject['name']}</b> – Choose a chapter:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


@router.callback_query(BackCD.filter(F.to == "top"))
async def cb_back_to_topics(
    cb: CallbackQuery, callback_data: BackCD, config: Config, repo: Repository
) -> None:
    chapter_id = callback_data.p1
    chapter = await repo.get_chapter(chapter_id)
    if not chapter:
        await cb.answer("Chapter not found", show_alert=True)
        return
    topics = await repo.get_topics_page(chapter_id, 0, config.ITEMS_PER_PAGE)
    total = await repo.count_topics(chapter_id)
    kb = build_user_topics_kb(
        topics, 0, total, config.ITEMS_PER_PAGE, chapter_id, chapter["subject_id"]
    )
    await cb.message.edit_text(
        f"📋 <b>{chapter['name']}</b> – Choose a topic:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


# ─────────────────────────────────────────────────────────────────────────────
# User: subject/chapter/topic pagination (UsrNavCD)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(UsrNavCD.filter(F.ctx == "s"))
async def cb_usr_nav_subjects(
    cb: CallbackQuery, callback_data: UsrNavCD, config: Config, repo: Repository
) -> None:
    page = callback_data.page
    subjects = await repo.get_subjects_page(page, config.ITEMS_PER_PAGE)
    total = await repo.count_subjects()
    kb = build_user_subjects_kb(subjects, page, total, config.ITEMS_PER_PAGE)
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer()


@router.callback_query(UsrNavCD.filter(F.ctx == "c"))
async def cb_usr_nav_chapters(
    cb: CallbackQuery, callback_data: UsrNavCD, config: Config, repo: Repository
) -> None:
    subject_id = callback_data.p1
    page = callback_data.page
    chapters = await repo.get_chapters_page(subject_id, page, config.ITEMS_PER_PAGE)
    total = await repo.count_chapters(subject_id)
    kb = build_user_chapters_kb(chapters, page, total, config.ITEMS_PER_PAGE, subject_id)
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer()


@router.callback_query(UsrNavCD.filter(F.ctx == "t"))
async def cb_usr_nav_topics(
    cb: CallbackQuery, callback_data: UsrNavCD, config: Config, repo: Repository
) -> None:
    chapter_id = callback_data.p1
    subject_id = callback_data.p2
    page = callback_data.page
    topics = await repo.get_topics_page(chapter_id, page, config.ITEMS_PER_PAGE)
    total = await repo.count_topics(chapter_id)
    kb = build_user_topics_kb(topics, page, total, config.ITEMS_PER_PAGE, chapter_id, subject_id)
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer()
