"""
handlers/admin.py – All administrator command handlers and FSM flows.

Flows implemented
─────────────────
1. Add Subject
2. Add Chapter
3. Add Topic
4. Upload Question (PDF)
5. Delete Question
6. List Questions
7. Statistics
8. Build ZIP Package
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database.repository import Repository
from filters.admin_filter import AdminFilter
from keyboards.admin_keyboard import (
    BTN_ADD_CHAPTER,
    BTN_ADD_SUBJECT,
    BTN_ADD_TOPIC,
    BTN_BUILD_ZIP,
    BTN_DELETE,
    BTN_LIST,
    BTN_STATS,
    BTN_UPLOAD,
    admin_main_keyboard,
)
from keyboards.inline_keyboard import (
    AdmChapCD,
    AdmNavCD,
    AdmQCD,
    AdmSubjCD,
    AdmTopCD,
    AdmDelConfCD,
    build_admin_chapters_kb,
    build_admin_questions_kb,
    build_admin_subjects_kb,
    build_admin_topics_kb,
    build_delete_confirm_kb,
)
from services.file_service import FileService
from services.query_service import QueryService
from services.zip_service import ZipService
from states.upload_states import (
    AddChapterStates,
    AddSubjectStates,
    AddTopicStates,
    BuildZipStates,
    DeleteQuestionStates,
    ListQuestionsStates,
    UploadQuestionStates,
)

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


# ════════════════════════════════════════════════════════════════════════════
#  /admin command
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "/admin")
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🔑 <b>Admin Panel</b>\n\nChoose an action from the menu below:",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


# ════════════════════════════════════════════════════════════════════════════
#  1. Add Subject
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_ADD_SUBJECT)
async def add_subject_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AddSubjectStates.waiting_name)
    await message.answer("📚 Enter the <b>subject name</b>:", parse_mode="HTML")


@router.message(AddSubjectStates.waiting_name, F.text)
async def add_subject_name(message: Message, state: FSMContext, repo: Repository) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("⚠️ Name cannot be empty. Try again:")
        return
    if len(name) > 100:
        await message.answer("⚠️ Name too long (max 100 chars). Try again:")
        return

    sid = await repo.add_subject(name)
    await state.clear()
    if sid:
        await message.answer(f"✅ Subject <b>{name}</b> added (ID: {sid}).", parse_mode="HTML")
    else:
        await message.answer("❌ Failed – subject may already exist.")


# ════════════════════════════════════════════════════════════════════════════
#  2. Add Chapter
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_ADD_CHAPTER)
async def add_chapter_start(
    message: Message, state: FSMContext, config: Config, repo: Repository
) -> None:
    subjects = await repo.get_subjects_page(0, config.ITEMS_PER_PAGE)
    total = await repo.count_subjects()
    if not subjects:
        await message.answer("⚠️ No subjects yet. Add a subject first.")
        return
    await state.set_state(AddChapterStates.selecting_subject)
    kb = build_admin_subjects_kb(subjects, 0, total, config.ITEMS_PER_PAGE)
    await message.answer("📚 Select a <b>subject</b>:", parse_mode="HTML", reply_markup=kb)


@router.callback_query(AdmSubjCD.filter(), AddChapterStates.selecting_subject)
async def add_chapter_subject_selected(
    cb: CallbackQuery, callback_data: AdmSubjCD, state: FSMContext, repo: Repository
) -> None:
    subject = await repo.get_subject(callback_data.sid)
    if not subject:
        await cb.answer("Subject not found.", show_alert=True)
        return
    await state.update_data(subject_id=subject["id"], subject_name=subject["name"])
    await state.set_state(AddChapterStates.waiting_name)
    await cb.message.edit_text(
        f"📂 Adding chapter to <b>{subject['name']}</b>\n\nEnter chapter name:",
        parse_mode="HTML",
    )
    await cb.answer()


@router.message(AddChapterStates.waiting_name, F.text)
async def add_chapter_name(message: Message, state: FSMContext, repo: Repository) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 100:
        await message.answer("⚠️ Invalid name (1–100 chars). Try again:")
        return
    data = await state.get_data()
    cid = await repo.add_chapter(data["subject_id"], name)
    await state.clear()
    if cid:
        await message.answer(
            f"✅ Chapter <b>{name}</b> added to <b>{data['subject_name']}</b>.",
            parse_mode="HTML",
        )
    else:
        await message.answer("❌ Failed – chapter may already exist in this subject.")


# ════════════════════════════════════════════════════════════════════════════
#  3. Add Topic
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_ADD_TOPIC)
async def add_topic_start(
    message: Message, state: FSMContext, config: Config, repo: Repository
) -> None:
    subjects = await repo.get_subjects_page(0, config.ITEMS_PER_PAGE)
    total = await repo.count_subjects()
    if not subjects:
        await message.answer("⚠️ No subjects yet.")
        return
    await state.set_state(AddTopicStates.selecting_subject)
    kb = build_admin_subjects_kb(subjects, 0, total, config.ITEMS_PER_PAGE)
    await message.answer("📚 Select a <b>subject</b>:", parse_mode="HTML", reply_markup=kb)


@router.callback_query(AdmSubjCD.filter(), AddTopicStates.selecting_subject)
async def add_topic_subject_selected(
    cb: CallbackQuery, callback_data: AdmSubjCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    subject = await repo.get_subject(callback_data.sid)
    if not subject:
        await cb.answer("Subject not found.", show_alert=True)
        return
    chapters = await repo.get_chapters_page(subject["id"], 0, config.ITEMS_PER_PAGE)
    total = await repo.count_chapters(subject["id"])
    if not chapters:
        await cb.answer("No chapters in this subject.", show_alert=True)
        return
    await state.update_data(subject_id=subject["id"], subject_name=subject["name"])
    await state.set_state(AddTopicStates.selecting_chapter)
    kb = build_admin_chapters_kb(chapters, 0, total, config.ITEMS_PER_PAGE, subject["id"])
    await cb.message.edit_text(
        f"📂 Subject: <b>{subject['name']}</b>\nSelect a <b>chapter</b>:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


@router.callback_query(AdmChapCD.filter(), AddTopicStates.selecting_chapter)
async def add_topic_chapter_selected(
    cb: CallbackQuery, callback_data: AdmChapCD, state: FSMContext, repo: Repository
) -> None:
    chapter = await repo.get_chapter(callback_data.cid)
    if not chapter:
        await cb.answer("Chapter not found.", show_alert=True)
        return
    await state.update_data(chapter_id=chapter["id"], chapter_name=chapter["name"])
    await state.set_state(AddTopicStates.waiting_name)
    await cb.message.edit_text(
        f"📋 Adding topic to <b>{chapter['name']}</b>\n\nEnter topic name:",
        parse_mode="HTML",
    )
    await cb.answer()


@router.message(AddTopicStates.waiting_name, F.text)
async def add_topic_name(message: Message, state: FSMContext, repo: Repository) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 100:
        await message.answer("⚠️ Invalid name (1–100 chars). Try again:")
        return
    data = await state.get_data()
    tid = await repo.add_topic(data["chapter_id"], name)
    await state.clear()
    if tid:
        await message.answer(
            f"✅ Topic <b>{name}</b> added to <b>{data['chapter_name']}</b>.",
            parse_mode="HTML",
        )
    else:
        await message.answer("❌ Failed – topic may already exist in this chapter.")


# ════════════════════════════════════════════════════════════════════════════
#  4. Upload Question
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_UPLOAD)
async def upload_start(
    message: Message, state: FSMContext, config: Config, repo: Repository
) -> None:
    subjects = await repo.get_subjects_page(0, config.ITEMS_PER_PAGE)
    total = await repo.count_subjects()
    if not subjects:
        await message.answer("⚠️ No subjects yet. Add one first.")
        return
    await state.set_state(UploadQuestionStates.selecting_subject)
    kb = build_admin_subjects_kb(subjects, 0, total, config.ITEMS_PER_PAGE)
    await message.answer("📚 Select <b>subject</b>:", parse_mode="HTML", reply_markup=kb)


@router.callback_query(AdmSubjCD.filter(), UploadQuestionStates.selecting_subject)
async def upload_subject_selected(
    cb: CallbackQuery, callback_data: AdmSubjCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    subject = await repo.get_subject(callback_data.sid)
    if not subject:
        await cb.answer("Subject not found.", show_alert=True)
        return
    chapters = await repo.get_chapters_page(subject["id"], 0, config.ITEMS_PER_PAGE)
    total = await repo.count_chapters(subject["id"])
    if not chapters:
        await cb.answer("No chapters in this subject.", show_alert=True)
        return
    await state.update_data(subject_id=subject["id"], subject_name=subject["name"])
    await state.set_state(UploadQuestionStates.selecting_chapter)
    kb = build_admin_chapters_kb(chapters, 0, total, config.ITEMS_PER_PAGE, subject["id"])
    await cb.message.edit_text(
        f"📂 Subject: <b>{subject['name']}</b>\nSelect <b>chapter</b>:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


@router.callback_query(AdmChapCD.filter(), UploadQuestionStates.selecting_chapter)
async def upload_chapter_selected(
    cb: CallbackQuery, callback_data: AdmChapCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    chapter = await repo.get_chapter(callback_data.cid)
    if not chapter:
        await cb.answer("Chapter not found.", show_alert=True)
        return
    topics = await repo.get_topics_page(chapter["id"], 0, config.ITEMS_PER_PAGE)
    total = await repo.count_topics(chapter["id"])
    if not topics:
        await cb.answer("No topics in this chapter.", show_alert=True)
        return
    await state.update_data(chapter_id=chapter["id"], chapter_name=chapter["name"])
    await state.set_state(UploadQuestionStates.selecting_topic)
    kb = build_admin_topics_kb(topics, 0, total, config.ITEMS_PER_PAGE, chapter["id"])
    await cb.message.edit_text(
        f"📋 Chapter: <b>{chapter['name']}</b>\nSelect <b>topic</b>:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


@router.callback_query(AdmTopCD.filter(), UploadQuestionStates.selecting_topic)
async def upload_topic_selected(
    cb: CallbackQuery, callback_data: AdmTopCD, state: FSMContext, repo: Repository
) -> None:
    topic = await repo.get_topic(callback_data.tid)
    if not topic:
        await cb.answer("Topic not found.", show_alert=True)
        return
    await state.update_data(topic_id=topic["id"], topic_name=topic["name"])
    await state.set_state(UploadQuestionStates.uploading_file)
    await cb.message.edit_text(
        f"📋 Topic: <b>{topic['name']}</b>\n\n"
        "📤 Now send the <b>PDF file</b>.\n"
        "Only PDF format is accepted.",
        parse_mode="HTML",
    )
    await cb.answer()


@router.message(UploadQuestionStates.uploading_file, F.document)
async def upload_file_received(
    message: Message, state: FSMContext,
    config: Config, repo: Repository,
    file_svc: FileService, zip_svc: ZipService
) -> None:
    doc = message.document
    if not doc:
        await message.answer("⚠️ No document received.")
        return

    original_name = doc.file_name or "unknown.pdf"

    # Basic MIME check before downloading
    if doc.mime_type and doc.mime_type != "application/pdf":
        await message.answer("❌ Only PDF files are accepted.")
        return

    if not original_name.lower().endswith(".pdf"):
        await message.answer("❌ File must have a .pdf extension.")
        return

    if doc.file_size and doc.file_size > config.max_file_size_bytes:
        await message.answer(
            f"❌ File too large ({doc.file_size // (1024*1024)} MB). "
            f"Max allowed: {config.MAX_FILE_SIZE_MB} MB."
        )
        return

    wait_msg = await message.answer("⏳ Downloading and saving…")

    try:
        file_info = await message.bot.get_file(doc.file_id)
        file_bytes = await message.bot.download_file(file_info.file_path)
        raw = file_bytes.read()
    except Exception as exc:
        logger.error("File download failed: %s", exc)
        await wait_msg.edit_text("❌ Download failed. Please try again.")
        return

    # Validate PDF magic bytes
    error = file_svc.validate_pdf(raw, original_name, config.max_file_size_bytes)
    if error:
        await wait_msg.edit_text(f"❌ Validation failed: {error}")
        return

    data = await state.get_data()
    try:
        file_name, file_path, file_size = await file_svc.save_pdf(
            raw,
            data["subject_name"],
            data["chapter_name"],
            data["topic_name"],
            original_name,
        )
    except Exception as exc:
        logger.error("File save failed: %s", exc)
        await wait_msg.edit_text("❌ Failed to save file. Check disk space.")
        return

    qid = await repo.add_question(
        data["topic_id"], file_name, file_path, original_name, file_size
    )

    if not qid:
        await wait_msg.edit_text("❌ Database save failed.")
        return

    await state.clear()

    # Regenerate ZIP
    all_questions = await repo.get_questions_by_topic(data["topic_id"])
    file_paths = [q["file_path"] for q in all_questions]
    await zip_svc.regenerate_zip(
        data["subject_name"], data["chapter_name"], data["topic_name"], file_paths
    )

    await wait_msg.edit_text(
        f"✅ <b>PDF uploaded successfully!</b>\n\n"
        f"📄 File: <code>{original_name}</code>\n"
        f"📏 Size: {file_size // 1024} KB\n"
        f"🆔 Question ID: {qid}\n"
        f"📋 Topic: {data['topic_name']}\n"
        f"📂 Chapter: {data['chapter_name']}\n"
        f"📚 Subject: {data['subject_name']}",
        parse_mode="HTML",
    )
    logger.info(
        "Admin %s uploaded: %s → %s (id=%s)",
        message.from_user.id, original_name, file_path, qid,
    )


@router.message(UploadQuestionStates.uploading_file)
async def upload_wrong_type(message: Message) -> None:
    await message.answer("⚠️ Please send a PDF document (not text or photo).")


# ════════════════════════════════════════════════════════════════════════════
#  5. Delete Question
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_DELETE)
async def delete_start(
    message: Message, state: FSMContext, config: Config, repo: Repository
) -> None:
    subjects = await repo.get_subjects_page(0, config.ITEMS_PER_PAGE)
    total = await repo.count_subjects()
    if not subjects:
        await message.answer("⚠️ No subjects yet.")
        return
    await state.set_state(DeleteQuestionStates.selecting_subject)
    kb = build_admin_subjects_kb(subjects, 0, total, config.ITEMS_PER_PAGE)
    await message.answer("🗑 Select <b>subject</b>:", parse_mode="HTML", reply_markup=kb)


@router.callback_query(AdmSubjCD.filter(), DeleteQuestionStates.selecting_subject)
async def delete_subject_selected(
    cb: CallbackQuery, callback_data: AdmSubjCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    subject = await repo.get_subject(callback_data.sid)
    if not subject:
        await cb.answer("Not found.", show_alert=True)
        return
    chapters = await repo.get_chapters_page(subject["id"], 0, config.ITEMS_PER_PAGE)
    total = await repo.count_chapters(subject["id"])
    if not chapters:
        await cb.answer("No chapters.", show_alert=True)
        return
    await state.update_data(subject_id=subject["id"], subject_name=subject["name"])
    await state.set_state(DeleteQuestionStates.selecting_chapter)
    kb = build_admin_chapters_kb(chapters, 0, total, config.ITEMS_PER_PAGE, subject["id"])
    await cb.message.edit_text("📂 Select <b>chapter</b>:", parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@router.callback_query(AdmChapCD.filter(), DeleteQuestionStates.selecting_chapter)
async def delete_chapter_selected(
    cb: CallbackQuery, callback_data: AdmChapCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    chapter = await repo.get_chapter(callback_data.cid)
    if not chapter:
        await cb.answer("Not found.", show_alert=True)
        return
    topics = await repo.get_topics_page(chapter["id"], 0, config.ITEMS_PER_PAGE)
    total = await repo.count_topics(chapter["id"])
    if not topics:
        await cb.answer("No topics.", show_alert=True)
        return
    await state.update_data(chapter_id=chapter["id"], chapter_name=chapter["name"])
    await state.set_state(DeleteQuestionStates.selecting_topic)
    kb = build_admin_topics_kb(topics, 0, total, config.ITEMS_PER_PAGE, chapter["id"])
    await cb.message.edit_text("📋 Select <b>topic</b>:", parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@router.callback_query(AdmTopCD.filter(), DeleteQuestionStates.selecting_topic)
async def delete_topic_selected(
    cb: CallbackQuery, callback_data: AdmTopCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    topic = await repo.get_topic(callback_data.tid)
    if not topic:
        await cb.answer("Not found.", show_alert=True)
        return
    questions = await repo.get_questions_page(topic["id"], 0, 20)
    total = await repo.count_questions(topic["id"])
    if not questions:
        await cb.answer("No questions in this topic.", show_alert=True)
        return
    await state.update_data(topic_id=topic["id"], topic_name=topic["name"])
    await state.set_state(DeleteQuestionStates.selecting_question)
    kb = build_admin_questions_kb(questions, 0, total, 20, topic["id"])
    await cb.message.edit_text(
        "🗑 Tap a <b>question</b> to delete it:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


@router.callback_query(AdmQCD.filter(), DeleteQuestionStates.selecting_question)
async def delete_question_selected(
    cb: CallbackQuery, callback_data: AdmQCD, state: FSMContext, repo: Repository
) -> None:
    question = await repo.get_question(callback_data.qid)
    if not question:
        await cb.answer("Question not found.", show_alert=True)
        return
    label = question.get("original_name") or question["file_name"]
    await state.update_data(question_id=question["id"])
    await state.set_state(DeleteQuestionStates.confirming)
    kb = build_delete_confirm_kb(question["id"], callback_data.tid)
    await cb.message.edit_text(
        f"⚠️ Delete <b>{label}</b>?\nThis action <u>cannot be undone</u>.",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await cb.answer()


@router.callback_query(AdmDelConfCD.filter(), DeleteQuestionStates.confirming)
async def delete_question_confirmed(
    cb: CallbackQuery, callback_data: AdmDelConfCD, state: FSMContext,
    repo: Repository, file_svc: FileService, zip_svc: ZipService
) -> None:
    question = await repo.get_question(callback_data.qid)
    if not question:
        await cb.answer("Already deleted.", show_alert=True)
        await state.clear()
        return

    path_info = await repo.get_topic_path(question["topic_id"])
    label = question.get("original_name") or question["file_name"]

    await repo.delete_question(callback_data.qid)
    await file_svc.delete_file(question["file_path"])
    await state.clear()

    # Regenerate ZIP
    if path_info:
        remaining = await repo.get_questions_by_topic(question["topic_id"])
        file_paths = [q["file_path"] for q in remaining]
        await zip_svc.regenerate_zip(
            path_info["subject_name"], path_info["chapter_name"], path_info["topic_name"], file_paths
        )

    await cb.message.edit_text(f"✅ Deleted: <b>{label}</b>", parse_mode="HTML")
    await cb.answer("Deleted!")
    logger.info("Admin %s deleted question id=%s (%s)", cb.from_user.id, callback_data.qid, label)


# ════════════════════════════════════════════════════════════════════════════
#  6. List Questions
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_LIST)
async def list_start(
    message: Message, state: FSMContext, config: Config, repo: Repository
) -> None:
    subjects = await repo.get_subjects_page(0, config.ITEMS_PER_PAGE)
    total = await repo.count_subjects()
    if not subjects:
        await message.answer("⚠️ No subjects yet.")
        return
    await state.set_state(ListQuestionsStates.selecting_subject)
    kb = build_admin_subjects_kb(subjects, 0, total, config.ITEMS_PER_PAGE)
    await message.answer("📋 Select <b>subject</b>:", parse_mode="HTML", reply_markup=kb)


@router.callback_query(AdmSubjCD.filter(), ListQuestionsStates.selecting_subject)
async def list_subject_selected(
    cb: CallbackQuery, callback_data: AdmSubjCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    subject = await repo.get_subject(callback_data.sid)
    if not subject:
        await cb.answer("Not found.", show_alert=True)
        return
    chapters = await repo.get_chapters_page(subject["id"], 0, config.ITEMS_PER_PAGE)
    total = await repo.count_chapters(subject["id"])
    if not chapters:
        await cb.answer("No chapters.", show_alert=True)
        return
    await state.update_data(subject_id=subject["id"])
    await state.set_state(ListQuestionsStates.selecting_chapter)
    kb = build_admin_chapters_kb(chapters, 0, total, config.ITEMS_PER_PAGE, subject["id"])
    await cb.message.edit_text("📂 Select <b>chapter</b>:", parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@router.callback_query(AdmChapCD.filter(), ListQuestionsStates.selecting_chapter)
async def list_chapter_selected(
    cb: CallbackQuery, callback_data: AdmChapCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    chapter = await repo.get_chapter(callback_data.cid)
    if not chapter:
        await cb.answer("Not found.", show_alert=True)
        return
    topics = await repo.get_topics_page(chapter["id"], 0, config.ITEMS_PER_PAGE)
    total = await repo.count_topics(chapter["id"])
    if not topics:
        await cb.answer("No topics.", show_alert=True)
        return
    await state.update_data(chapter_id=chapter["id"])
    await state.set_state(ListQuestionsStates.selecting_topic)
    kb = build_admin_topics_kb(topics, 0, total, config.ITEMS_PER_PAGE, chapter["id"])
    await cb.message.edit_text("📋 Select <b>topic</b>:", parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@router.callback_query(AdmTopCD.filter(), ListQuestionsStates.selecting_topic)
async def list_topic_selected(
    cb: CallbackQuery, callback_data: AdmTopCD, state: FSMContext, repo: Repository
) -> None:
    topic = await repo.get_topic(callback_data.tid)
    if not topic:
        await cb.answer("Not found.", show_alert=True)
        return
    questions = await repo.get_questions_by_topic(topic["id"])
    await state.clear()
    if not questions:
        await cb.message.edit_text(f"📋 <b>{topic['name']}</b> – no questions yet.", parse_mode="HTML")
        await cb.answer()
        return
    lines = [f"📋 <b>{topic['name']}</b> – {len(questions)} PDF(s):\n"]
    for i, q in enumerate(questions, 1):
        label = q.get("original_name") or q["file_name"]
        size_kb = q.get("file_size", 0) // 1024
        lines.append(f"{i}. {label} ({size_kb} KB) [ID: {q['id']}]")
    await cb.message.edit_text("\n".join(lines), parse_mode="HTML")
    await cb.answer()


# ════════════════════════════════════════════════════════════════════════════
#  7. Statistics
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_STATS)
@router.message(F.text == "/stats")
async def cmd_stats(message: Message, query_svc: QueryService) -> None:
    text = await query_svc.get_stats_text()
    await message.answer(text, parse_mode="HTML")


# ════════════════════════════════════════════════════════════════════════════
#  8. Build ZIP Package
# ════════════════════════════════════════════════════════════════════════════

@router.message(F.text == BTN_BUILD_ZIP)
async def build_zip_start(
    message: Message, state: FSMContext, config: Config, repo: Repository
) -> None:
    subjects = await repo.get_subjects_page(0, config.ITEMS_PER_PAGE)
    total = await repo.count_subjects()
    if not subjects:
        await message.answer("⚠️ No subjects yet.")
        return
    await state.set_state(BuildZipStates.selecting_subject)
    kb = build_admin_subjects_kb(subjects, 0, total, config.ITEMS_PER_PAGE)
    await message.answer("📦 Select <b>subject</b>:", parse_mode="HTML", reply_markup=kb)


@router.callback_query(AdmSubjCD.filter(), BuildZipStates.selecting_subject)
async def build_zip_subject(
    cb: CallbackQuery, callback_data: AdmSubjCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    subject = await repo.get_subject(callback_data.sid)
    if not subject:
        await cb.answer("Not found.", show_alert=True)
        return
    chapters = await repo.get_chapters_page(subject["id"], 0, config.ITEMS_PER_PAGE)
    total = await repo.count_chapters(subject["id"])
    if not chapters:
        await cb.answer("No chapters.", show_alert=True)
        return
    await state.update_data(subject_id=subject["id"], subject_name=subject["name"])
    await state.set_state(BuildZipStates.selecting_chapter)
    kb = build_admin_chapters_kb(chapters, 0, total, config.ITEMS_PER_PAGE, subject["id"])
    await cb.message.edit_text("📂 Select <b>chapter</b>:", parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@router.callback_query(AdmChapCD.filter(), BuildZipStates.selecting_chapter)
async def build_zip_chapter(
    cb: CallbackQuery, callback_data: AdmChapCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    chapter = await repo.get_chapter(callback_data.cid)
    if not chapter:
        await cb.answer("Not found.", show_alert=True)
        return
    topics = await repo.get_topics_page(chapter["id"], 0, config.ITEMS_PER_PAGE)
    total = await repo.count_topics(chapter["id"])
    if not topics:
        await cb.answer("No topics.", show_alert=True)
        return
    await state.update_data(chapter_id=chapter["id"], chapter_name=chapter["name"])
    await state.set_state(BuildZipStates.selecting_topic)
    kb = build_admin_topics_kb(topics, 0, total, config.ITEMS_PER_PAGE, chapter["id"])
    await cb.message.edit_text("📋 Select <b>topic</b>:", parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@router.callback_query(AdmTopCD.filter(), BuildZipStates.selecting_topic)
async def build_zip_topic(
    cb: CallbackQuery, callback_data: AdmTopCD, state: FSMContext,
    repo: Repository, zip_svc: ZipService
) -> None:
    topic = await repo.get_topic(callback_data.tid)
    if not topic:
        await cb.answer("Not found.", show_alert=True)
        return
    data = await state.get_data()
    await state.clear()

    questions = await repo.get_questions_by_topic(topic["id"])
    if not questions:
        await cb.message.edit_text("⚠️ No questions in this topic.")
        await cb.answer()
        return

    wait_msg = await cb.message.edit_text(
        f"⏳ Building ZIP for <b>{topic['name']}</b> ({len(questions)} files)…",
        parse_mode="HTML",
    )
    await cb.answer()

    file_paths = [q["file_path"] for q in questions]
    ok = await zip_svc.regenerate_zip(
        data["subject_name"], data["chapter_name"], topic["name"], file_paths
    )

    if ok:
        zip_path = zip_svc.zip_path(data["subject_name"], data["chapter_name"], topic["name"])
        size_mb = zip_path.stat().st_size / 1_048_576
        await wait_msg.edit_text(
            f"✅ ZIP built for <b>{topic['name']}</b>\n"
            f"📦 {len(questions)} files, {size_mb:.1f} MB",
            parse_mode="HTML",
        )
        logger.info("Admin %s built ZIP for topic %s", cb.from_user.id, topic["id"])
    else:
        await wait_msg.edit_text("❌ ZIP build failed. Check logs.")


# ════════════════════════════════════════════════════════════════════════════
#  Pagination for admin navigation callbacks (shared across flows)
# ════════════════════════════════════════════════════════════════════════════

@router.callback_query(AdmNavCD.filter())
async def adm_nav(
    cb: CallbackQuery, callback_data: AdmNavCD, state: FSMContext,
    config: Config, repo: Repository
) -> None:
    ctx  = callback_data.ctx
    page = callback_data.page
    pid  = callback_data.pid

    if ctx == "s":
        subjects = await repo.get_subjects_page(page, config.ITEMS_PER_PAGE)
        total = await repo.count_subjects()
        kb = build_admin_subjects_kb(subjects, page, total, config.ITEMS_PER_PAGE)
        await cb.message.edit_reply_markup(reply_markup=kb)

    elif ctx == "c":
        chapters = await repo.get_chapters_page(pid, page, config.ITEMS_PER_PAGE)
        total = await repo.count_chapters(pid)
        kb = build_admin_chapters_kb(chapters, page, total, config.ITEMS_PER_PAGE, pid)
        await cb.message.edit_reply_markup(reply_markup=kb)

    elif ctx == "t":
        topics = await repo.get_topics_page(pid, page, config.ITEMS_PER_PAGE)
        total = await repo.count_topics(pid)
        kb = build_admin_topics_kb(topics, page, total, config.ITEMS_PER_PAGE, pid)
        await cb.message.edit_reply_markup(reply_markup=kb)

    elif ctx == "q":
        questions = await repo.get_questions_page(pid, page, config.ITEMS_PER_PAGE)
        total = await repo.count_questions(pid)
        kb = build_admin_questions_kb(questions, page, total, config.ITEMS_PER_PAGE, pid)
        await cb.message.edit_reply_markup(reply_markup=kb)

    await cb.answer()
