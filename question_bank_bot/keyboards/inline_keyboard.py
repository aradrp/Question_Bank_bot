"""
keyboards/inline_keyboard.py
────────────────────────────
CallbackData classes (prefixes are kept short to stay well inside
Telegram's 64-byte callback-data limit) and InlineKeyboardBuilder
helper functions used across admin and user handlers.
"""
from __future__ import annotations

import math
from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ═══════════════════════════════════════════════════════════════════════════
#  Callback-data classes
# ═══════════════════════════════════════════════════════════════════════════

# ── Admin: item selection ────────────────────────────────────────────────
class AdmSubjCD(CallbackData, prefix="as"):
    sid: int
    page: int = 0


class AdmChapCD(CallbackData, prefix="ac"):
    cid: int
    sid: int
    page: int = 0


class AdmTopCD(CallbackData, prefix="at"):
    tid: int
    cid: int
    page: int = 0


class AdmQCD(CallbackData, prefix="aq"):
    qid: int
    tid: int
    page: int = 0


# ── Admin: pagination navigation ─────────────────────────────────────────
class AdmNavCD(CallbackData, prefix="an"):
    ctx: str   # "s"=subjects, "c"=chapters, "t"=topics, "q"=questions
    page: int
    pid: int = 0   # parent id required for c/t/q


# ── Admin: destructive action confirmations ───────────────────────────────
class AdmDelConfCD(CallbackData, prefix="adc"):
    qid: int
    tid: int


class AdmCancelCD(CallbackData, prefix="axl"):
    pass


# ── User: browsing ────────────────────────────────────────────────────────
class UsrSubjCD(CallbackData, prefix="us"):
    sid: int
    page: int = 0


class UsrChapCD(CallbackData, prefix="uc"):
    cid: int
    sid: int
    page: int = 0


class UsrTopCD(CallbackData, prefix="ut"):
    tid: int
    cid: int
    page: int = 0


class UsrQCD(CallbackData, prefix="uq"):
    qid: int
    tid: int
    page: int = 0


class UsrZipCD(CallbackData, prefix="uz"):
    tid: int


class UsrAllCD(CallbackData, prefix="ua"):
    tid: int


# ── User: navigation ──────────────────────────────────────────────────────
class UsrNavCD(CallbackData, prefix="un"):
    ctx: str    # "s","c","t","q"
    page: int
    p1: int = 0   # parent id 1
    p2: int = 0   # parent id 2 (for q context: cid + sid)


# ── Shared: back ─────────────────────────────────────────────────────────
class BackCD(CallbackData, prefix="bk"):
    to: str     # "subj","chap","top"
    p1: int = 0
    p2: int = 0


# ═══════════════════════════════════════════════════════════════════════════
#  Shared pagination helper
# ═══════════════════════════════════════════════════════════════════════════

def _nav_row(
    page: int,
    total: int,
    per_page: int,
    nav_cd_prev,
    nav_cd_next,
) -> list[InlineKeyboardButton]:
    """Return 1-3 navigation buttons [⬅ | Page X/Y | ➡]."""
    total_pages = max(1, math.ceil(total / per_page))
    buttons: list[InlineKeyboardButton] = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=nav_cd_prev.pack()))
    buttons.append(InlineKeyboardButton(
        text=f"📄 {page + 1}/{total_pages}", callback_data="noop"
    ))
    if (page + 1) * per_page < total:
        buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=nav_cd_next.pack()))
    return buttons


# ═══════════════════════════════════════════════════════════════════════════
#  Admin keyboards
# ═══════════════════════════════════════════════════════════════════════════

def build_admin_subjects_kb(
    subjects: List[dict],
    page: int,
    total: int,
    per_page: int,
    cancel: bool = True,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in subjects:
        b.button(text=f"📚 {s['name']}", callback_data=AdmSubjCD(sid=s["id"], page=page).pack())
    b.adjust(1)
    if total > per_page:
        b.row(*_nav_row(
            page, total, per_page,
            AdmNavCD(ctx="s", page=page - 1, pid=0),
            AdmNavCD(ctx="s", page=page + 1, pid=0),
        ))
    if cancel:
        b.row(InlineKeyboardButton(text="❌ Cancel", callback_data=AdmCancelCD().pack()))
    return b.as_markup()


def build_admin_chapters_kb(
    chapters: List[dict],
    page: int,
    total: int,
    per_page: int,
    subject_id: int,
    cancel: bool = True,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in chapters:
        b.button(
            text=f"📂 {c['name']}",
            callback_data=AdmChapCD(cid=c["id"], sid=subject_id, page=page).pack(),
        )
    b.adjust(1)
    if total > per_page:
        b.row(*_nav_row(
            page, total, per_page,
            AdmNavCD(ctx="c", page=page - 1, pid=subject_id),
            AdmNavCD(ctx="c", page=page + 1, pid=subject_id),
        ))
    if cancel:
        b.row(InlineKeyboardButton(text="❌ Cancel", callback_data=AdmCancelCD().pack()))
    return b.as_markup()


def build_admin_topics_kb(
    topics: List[dict],
    page: int,
    total: int,
    per_page: int,
    chapter_id: int,
    cancel: bool = True,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in topics:
        b.button(
            text=f"📋 {t['name']}",
            callback_data=AdmTopCD(tid=t["id"], cid=chapter_id, page=page).pack(),
        )
    b.adjust(1)
    if total > per_page:
        b.row(*_nav_row(
            page, total, per_page,
            AdmNavCD(ctx="t", page=page - 1, pid=chapter_id),
            AdmNavCD(ctx="t", page=page + 1, pid=chapter_id),
        ))
    if cancel:
        b.row(InlineKeyboardButton(text="❌ Cancel", callback_data=AdmCancelCD().pack()))
    return b.as_markup()


def build_admin_questions_kb(
    questions: List[dict],
    page: int,
    total: int,
    per_page: int,
    topic_id: int,
    cancel: bool = True,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for q in questions:
        label = q.get("original_name") or q["file_name"]
        b.button(
            text=f"🗑 {label}",
            callback_data=AdmQCD(qid=q["id"], tid=topic_id, page=page).pack(),
        )
    b.adjust(1)
    if total > per_page:
        b.row(*_nav_row(
            page, total, per_page,
            AdmNavCD(ctx="q", page=page - 1, pid=topic_id),
            AdmNavCD(ctx="q", page=page + 1, pid=topic_id),
        ))
    if cancel:
        b.row(InlineKeyboardButton(text="❌ Cancel", callback_data=AdmCancelCD().pack()))
    return b.as_markup()


def build_delete_confirm_kb(question_id: int, topic_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(
        text="✅ Confirm Delete",
        callback_data=AdmDelConfCD(qid=question_id, tid=topic_id).pack(),
    )
    b.button(text="❌ Cancel", callback_data=AdmCancelCD().pack())
    b.adjust(2)
    return b.as_markup()


# ═══════════════════════════════════════════════════════════════════════════
#  User keyboards
# ═══════════════════════════════════════════════════════════════════════════

def build_user_subjects_kb(
    subjects: List[dict],
    page: int,
    total: int,
    per_page: int,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in subjects:
        b.button(text=f"📚 {s['name']}", callback_data=UsrSubjCD(sid=s["id"], page=page).pack())
    b.adjust(1)
    if total > per_page:
        b.row(*_nav_row(
            page, total, per_page,
            UsrNavCD(ctx="s", page=page - 1),
            UsrNavCD(ctx="s", page=page + 1),
        ))
    return b.as_markup()


def build_user_chapters_kb(
    chapters: List[dict],
    page: int,
    total: int,
    per_page: int,
    subject_id: int,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in chapters:
        b.button(
            text=f"📂 {c['name']}",
            callback_data=UsrChapCD(cid=c["id"], sid=subject_id, page=page).pack(),
        )
    b.adjust(1)
    if total > per_page:
        b.row(*_nav_row(
            page, total, per_page,
            UsrNavCD(ctx="c", page=page - 1, p1=subject_id),
            UsrNavCD(ctx="c", page=page + 1, p1=subject_id),
        ))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data=BackCD(to="subj").pack()))
    return b.as_markup()


def build_user_topics_kb(
    topics: List[dict],
    page: int,
    total: int,
    per_page: int,
    chapter_id: int,
    subject_id: int,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in topics:
        b.button(
            text=f"📋 {t['name']}",
            callback_data=UsrTopCD(tid=t["id"], cid=chapter_id, page=page).pack(),
        )
    b.adjust(1)
    if total > per_page:
        b.row(*_nav_row(
            page, total, per_page,
            UsrNavCD(ctx="t", page=page - 1, p1=chapter_id, p2=subject_id),
            UsrNavCD(ctx="t", page=page + 1, p1=chapter_id, p2=subject_id),
        ))
    b.row(InlineKeyboardButton(
        text="⬅️ Back",
        callback_data=BackCD(to="chap", p1=subject_id).pack(),
    ))
    return b.as_markup()


def build_user_questions_kb(
    questions: List[dict],
    page: int,
    total: int,
    per_page: int,
    topic_id: int,
    chapter_id: int,
    has_zip: bool = False,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for q in questions:
        label = q.get("original_name") or q["file_name"]
        b.button(
            text=f"📄 {label}",
            callback_data=UsrQCD(qid=q["id"], tid=topic_id, page=page).pack(),
        )
    b.adjust(1)
    if total > per_page:
        b.row(*_nav_row(
            page, total, per_page,
            UsrNavCD(ctx="q", page=page - 1, p1=topic_id, p2=chapter_id),
            UsrNavCD(ctx="q", page=page + 1, p1=topic_id, p2=chapter_id),
        ))
    # Action row
    action_btns: list[InlineKeyboardButton] = []
    if has_zip:
        action_btns.append(InlineKeyboardButton(
            text="📦 Download ZIP",
            callback_data=UsrZipCD(tid=topic_id).pack(),
        ))
    action_btns.append(InlineKeyboardButton(
        text="📂 Download All PDFs",
        callback_data=UsrAllCD(tid=topic_id).pack(),
    ))
    if action_btns:
        b.row(*action_btns)
    b.row(InlineKeyboardButton(
        text="⬅️ Back",
        callback_data=BackCD(to="top", p1=chapter_id).pack(),
    ))
    return b.as_markup()
