"""
handlers/user.py – User-facing browsing and download handlers.
"""
from __future__ import annotations

import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, FSInputFile

from config import Config
from database.repository import Repository
from keyboards.inline_keyboard import (
    UsrAllCD,
    UsrChapCD,
    UsrNavCD,
    UsrQCD,
    UsrSubjCD,
    UsrTopCD,
    UsrZipCD,
    build_user_chapters_kb,
    build_user_questions_kb,
    build_user_subjects_kb,
    build_user_topics_kb,
)
from services.file_service import FileService
from services.zip_service import ZipService

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Subject selected
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(UsrSubjCD.filter())
async def cb_subject(
    cb: CallbackQuery, callback_data: UsrSubjCD, config: Config, repo: Repository
) -> None:
    subject_id = callback_data.sid
    subject = await repo.get_subject(subject_id)
    if not subject:
        await cb.answer("Subject not found.", show_alert=True)
        return

    chapters = await repo.get_chapters_page(subject_id, 0, config.ITEMS_PER_PAGE)
    total = await repo.count_chapters(subject_id)

    if not chapters:
        await cb.answer("No chapters in this subject yet.", show_alert=True)
        return

    kb = build_user_chapters_kb(chapters, 0, total, config.ITEMS_PER_PAGE, subject_id)
    await cb.message.edit_text(
        f"📚 <b>{subject['name']}</b>\n📂 Choose a chapter:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Chapter selected
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(UsrChapCD.filter())
async def cb_chapter(
    cb: CallbackQuery, callback_data: UsrChapCD, config: Config, repo: Repository
) -> None:
    chapter_id = callback_data.cid
    subject_id = callback_data.sid
    chapter = await repo.get_chapter(chapter_id)
    if not chapter:
        await cb.answer("Chapter not found.", show_alert=True)
        return

    topics = await repo.get_topics_page(chapter_id, 0, config.ITEMS_PER_PAGE)
    total = await repo.count_topics(chapter_id)

    if not topics:
        await cb.answer("No topics in this chapter yet.", show_alert=True)
        return

    kb = build_user_topics_kb(topics, 0, total, config.ITEMS_PER_PAGE, chapter_id, subject_id)
    await cb.message.edit_text(
        f"📂 <b>{chapter['name']}</b>\n📋 Choose a topic:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Topic selected – show question list
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(UsrTopCD.filter())
async def cb_topic(
    cb: CallbackQuery, callback_data: UsrTopCD, config: Config,
    repo: Repository, zip_svc: ZipService
) -> None:
    topic_id = callback_data.tid
    chapter_id = callback_data.cid
    topic = await repo.get_topic(topic_id)
    if not topic:
        await cb.answer("Topic not found.", show_alert=True)
        return

    questions = await repo.get_questions_page(topic_id, 0, config.ITEMS_PER_PAGE)
    total = await repo.count_questions(topic_id)

    if not questions:
        await cb.answer("No questions in this topic yet.", show_alert=True)
        return

    path_info = await repo.get_topic_path(topic_id)
    has_zip = False
    if path_info:
        has_zip = zip_svc.zip_exists(
            path_info["subject_name"], path_info["chapter_name"], path_info["topic_name"]
        )

    kb = build_user_questions_kb(
        questions, 0, total, config.ITEMS_PER_PAGE, topic_id, chapter_id, has_zip
    )
    await cb.message.edit_text(
        f"📋 <b>{topic['name']}</b>\n"
        f"📄 {total} PDF(s) available – tap one to download:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Question pagination
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(UsrNavCD.filter(F.ctx == "q"))
async def cb_usr_nav_questions(
    cb: CallbackQuery, callback_data: UsrNavCD, config: Config,
    repo: Repository, zip_svc: ZipService
) -> None:
    topic_id = callback_data.p1
    chapter_id = callback_data.p2
    page = callback_data.page
    questions = await repo.get_questions_page(topic_id, page, config.ITEMS_PER_PAGE)
    total = await repo.count_questions(topic_id)

    path_info = await repo.get_topic_path(topic_id)
    has_zip = False
    if path_info:
        has_zip = zip_svc.zip_exists(
            path_info["subject_name"], path_info["chapter_name"], path_info["topic_name"]
        )

    kb = build_user_questions_kb(
        questions, page, total, config.ITEMS_PER_PAGE, topic_id, chapter_id, has_zip
    )
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Single PDF download
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(UsrQCD.filter())
async def cb_download_question(
    cb: CallbackQuery, callback_data: UsrQCD, repo: Repository, file_svc: FileService
) -> None:
    question = await repo.get_question(callback_data.qid)
    if not question:
        await cb.answer("File not found.", show_alert=True)
        return

    if not file_svc.file_exists(question["file_path"]):
        await cb.answer("File missing on server. Contact admin.", show_alert=True)
        logger.error("Missing file: %s (id=%s)", question["file_path"], question["id"])
        return

    await cb.answer("📄 Sending PDF…")
    doc = FSInputFile(question["file_path"], filename=question.get("original_name") or question["file_name"])
    await cb.message.answer_document(doc, caption=f"📄 {question.get('original_name') or question['file_name']}")
    logger.info("User %s downloaded question id=%s", cb.from_user.id, question["id"])


# ─────────────────────────────────────────────────────────────────────────────
# Download all PDFs one by one
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(UsrAllCD.filter())
async def cb_download_all(
    cb: CallbackQuery, callback_data: UsrAllCD, repo: Repository, file_svc: FileService
) -> None:
    topic_id = callback_data.tid
    questions = await repo.get_questions_by_topic(topic_id)

    if not questions:
        await cb.answer("No files available.", show_alert=True)
        return

    await cb.answer(f"📂 Sending {len(questions)} file(s)…")
    await cb.message.answer(f"📂 Sending <b>{len(questions)}</b> PDF(s), please wait…", parse_mode="HTML")

    sent = 0
    for q in questions:
        if file_svc.file_exists(q["file_path"]):
            doc = FSInputFile(q["file_path"], filename=q.get("original_name") or q["file_name"])
            await cb.message.answer_document(doc)
            sent += 1
        else:
            logger.warning("Missing file during bulk send: %s", q["file_path"])

    await cb.message.answer(f"✅ Sent <b>{sent}</b> of <b>{len(questions)}</b> file(s).", parse_mode="HTML")
    logger.info("User %s bulk-downloaded %d files for topic %s", cb.from_user.id, sent, topic_id)


# ─────────────────────────────────────────────────────────────────────────────
# Download ZIP
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(UsrZipCD.filter())
async def cb_download_zip(
    cb: CallbackQuery, callback_data: UsrZipCD,
    repo: Repository, zip_svc: ZipService
) -> None:
    topic_id = callback_data.tid
    path_info = await repo.get_topic_path(topic_id)
    if not path_info:
        await cb.answer("Topic not found.", show_alert=True)
        return

    zip_path = zip_svc.zip_path(
        path_info["subject_name"], path_info["chapter_name"], path_info["topic_name"]
    )

    if not zip_path.is_file():
        await cb.answer("ZIP not ready. Try again in a moment.", show_alert=True)
        return

    size_mb = zip_path.stat().st_size / 1_048_576
    await cb.answer(f"📦 Sending ZIP ({size_mb:.1f} MB)…")

    doc = FSInputFile(str(zip_path), filename=zip_path.name)
    await cb.message.answer_document(
        doc,
        caption=(
            f"📦 <b>{path_info['topic_name']}</b>\n"
            f"Subject: {path_info['subject_name']}\n"
            f"Chapter: {path_info['chapter_name']}\n"
            f"Size: {size_mb:.1f} MB"
        ),
        parse_mode="HTML",
    )
    logger.info("User %s downloaded ZIP for topic %s", cb.from_user.id, topic_id)
