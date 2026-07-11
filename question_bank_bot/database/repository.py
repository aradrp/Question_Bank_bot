"""
database/repository.py – Data-access layer (Repository pattern).

All public methods return plain Python dicts (converted from aiosqlite.Row)
or primitive types so that callers never depend on DB internals.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from database.db import Database

logger = logging.getLogger(__name__)

Row = Dict[str, Any]


def _row(r) -> Optional[Row]:
    return dict(r) if r else None


def _rows(rs) -> List[Row]:
    return [dict(r) for r in rs]


class Repository:
    """Single-repository that handles all entities."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ════════════════════════════════════════════════════════════════════════
    #  Subjects
    # ════════════════════════════════════════════════════════════════════════

    async def add_subject(self, name: str) -> Optional[int]:
        try:
            cur = await self.db.execute(
                "INSERT INTO subjects (name) VALUES (?)", (name.strip(),)
            )
            logger.info("Subject added: %s (id=%s)", name, cur.lastrowid)
            return cur.lastrowid
        except Exception as exc:
            logger.warning("add_subject failed: %s", exc)
            return None

    async def get_subject(self, subject_id: int) -> Optional[Row]:
        return _row(await self.db.fetchone(
            "SELECT * FROM subjects WHERE id = ?", (subject_id,)
        ))

    async def get_subject_by_name(self, name: str) -> Optional[Row]:
        return _row(await self.db.fetchone(
            "SELECT * FROM subjects WHERE name = ? COLLATE NOCASE", (name.strip(),)
        ))

    async def get_all_subjects(self) -> List[Row]:
        return _rows(await self.db.fetchall(
            "SELECT * FROM subjects ORDER BY name"
        ))

    async def get_subjects_page(self, page: int, per_page: int) -> List[Row]:
        offset = page * per_page
        return _rows(await self.db.fetchall(
            "SELECT * FROM subjects ORDER BY name LIMIT ? OFFSET ?",
            (per_page, offset),
        ))

    async def count_subjects(self) -> int:
        return await self.db.fetchscalar("SELECT COUNT(*) FROM subjects") or 0

    async def delete_subject(self, subject_id: int) -> bool:
        await self.db.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
        logger.info("Subject deleted: id=%s", subject_id)
        return True

    # ════════════════════════════════════════════════════════════════════════
    #  Chapters
    # ════════════════════════════════════════════════════════════════════════

    async def add_chapter(self, subject_id: int, name: str) -> Optional[int]:
        try:
            cur = await self.db.execute(
                "INSERT INTO chapters (subject_id, name) VALUES (?, ?)",
                (subject_id, name.strip()),
            )
            logger.info("Chapter added: %s under subject %s (id=%s)", name, subject_id, cur.lastrowid)
            return cur.lastrowid
        except Exception as exc:
            logger.warning("add_chapter failed: %s", exc)
            return None

    async def get_chapter(self, chapter_id: int) -> Optional[Row]:
        return _row(await self.db.fetchone(
            "SELECT * FROM chapters WHERE id = ?", (chapter_id,)
        ))

    async def get_chapters_by_subject(self, subject_id: int) -> List[Row]:
        return _rows(await self.db.fetchall(
            "SELECT * FROM chapters WHERE subject_id = ? ORDER BY name", (subject_id,)
        ))

    async def get_chapters_page(self, subject_id: int, page: int, per_page: int) -> List[Row]:
        offset = page * per_page
        return _rows(await self.db.fetchall(
            "SELECT * FROM chapters WHERE subject_id = ? ORDER BY name LIMIT ? OFFSET ?",
            (subject_id, per_page, offset),
        ))

    async def count_chapters(self, subject_id: int) -> int:
        return await self.db.fetchscalar(
            "SELECT COUNT(*) FROM chapters WHERE subject_id = ?", (subject_id,)
        ) or 0

    async def delete_chapter(self, chapter_id: int) -> bool:
        await self.db.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
        logger.info("Chapter deleted: id=%s", chapter_id)
        return True

    # ════════════════════════════════════════════════════════════════════════
    #  Topics
    # ════════════════════════════════════════════════════════════════════════

    async def add_topic(self, chapter_id: int, name: str) -> Optional[int]:
        try:
            cur = await self.db.execute(
                "INSERT INTO topics (chapter_id, name) VALUES (?, ?)",
                (chapter_id, name.strip()),
            )
            logger.info("Topic added: %s under chapter %s (id=%s)", name, chapter_id, cur.lastrowid)
            return cur.lastrowid
        except Exception as exc:
            logger.warning("add_topic failed: %s", exc)
            return None

    async def get_topic(self, topic_id: int) -> Optional[Row]:
        return _row(await self.db.fetchone(
            "SELECT * FROM topics WHERE id = ?", (topic_id,)
        ))

    async def get_topics_by_chapter(self, chapter_id: int) -> List[Row]:
        return _rows(await self.db.fetchall(
            "SELECT * FROM topics WHERE chapter_id = ? ORDER BY name", (chapter_id,)
        ))

    async def get_topics_page(self, chapter_id: int, page: int, per_page: int) -> List[Row]:
        offset = page * per_page
        return _rows(await self.db.fetchall(
            "SELECT * FROM topics WHERE chapter_id = ? ORDER BY name LIMIT ? OFFSET ?",
            (chapter_id, per_page, offset),
        ))

    async def count_topics(self, chapter_id: int) -> int:
        return await self.db.fetchscalar(
            "SELECT COUNT(*) FROM topics WHERE chapter_id = ?", (chapter_id,)
        ) or 0

    async def delete_topic(self, topic_id: int) -> bool:
        await self.db.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        logger.info("Topic deleted: id=%s", topic_id)
        return True

    # ════════════════════════════════════════════════════════════════════════
    #  Questions
    # ════════════════════════════════════════════════════════════════════════

    async def add_question(
        self,
        topic_id: int,
        file_name: str,
        file_path: str,
        original_name: str = "",
        file_size: int = 0,
    ) -> Optional[int]:
        try:
            cur = await self.db.execute(
                """INSERT INTO questions
                   (topic_id, file_name, file_path, original_name, file_size)
                   VALUES (?, ?, ?, ?, ?)""",
                (topic_id, file_name, file_path, original_name, file_size),
            )
            logger.info(
                "Question added: %s → %s (id=%s)", original_name, file_path, cur.lastrowid
            )
            return cur.lastrowid
        except Exception as exc:
            logger.warning("add_question failed: %s", exc)
            return None

    async def get_question(self, question_id: int) -> Optional[Row]:
        return _row(await self.db.fetchone(
            "SELECT * FROM questions WHERE id = ?", (question_id,)
        ))

    async def get_questions_by_topic(self, topic_id: int) -> List[Row]:
        return _rows(await self.db.fetchall(
            "SELECT * FROM questions WHERE topic_id = ? ORDER BY upload_date, file_name",
            (topic_id,),
        ))

    async def get_questions_page(self, topic_id: int, page: int, per_page: int) -> List[Row]:
        offset = page * per_page
        return _rows(await self.db.fetchall(
            """SELECT * FROM questions WHERE topic_id = ?
               ORDER BY upload_date, file_name LIMIT ? OFFSET ?""",
            (topic_id, per_page, offset),
        ))

    async def count_questions(self, topic_id: int) -> int:
        return await self.db.fetchscalar(
            "SELECT COUNT(*) FROM questions WHERE topic_id = ?", (topic_id,)
        ) or 0

    async def delete_question(self, question_id: int) -> bool:
        await self.db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        logger.info("Question deleted: id=%s", question_id)
        return True

    # ════════════════════════════════════════════════════════════════════════
    #  Admins
    # ════════════════════════════════════════════════════════════════════════

    async def add_admin(self, telegram_id: int) -> bool:
        try:
            await self.db.execute(
                "INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)", (telegram_id,)
            )
            return True
        except Exception as exc:
            logger.warning("add_admin failed: %s", exc)
            return False

    async def is_admin(self, telegram_id: int) -> bool:
        row = await self.db.fetchone(
            "SELECT 1 FROM admins WHERE telegram_id = ?", (telegram_id,)
        )
        return row is not None

    async def get_all_admins(self) -> List[Row]:
        return _rows(await self.db.fetchall("SELECT * FROM admins ORDER BY added_at"))

    # ════════════════════════════════════════════════════════════════════════
    #  Aggregate / navigation helpers
    # ════════════════════════════════════════════════════════════════════════

    async def get_topic_path(self, topic_id: int) -> Optional[dict]:
        """Return a dict with subject/chapter/topic names for a given topic_id."""
        row = await self.db.fetchone(
            """SELECT s.name AS subject_name,
                      c.name AS chapter_name,
                      t.name AS topic_name,
                      s.id   AS subject_id,
                      c.id   AS chapter_id,
                      t.id   AS topic_id
               FROM topics t
               JOIN chapters c ON c.id = t.chapter_id
               JOIN subjects s ON s.id = c.subject_id
               WHERE t.id = ?""",
            (topic_id,),
        )
        return _row(row)

    async def get_statistics(self) -> dict:
        """Return counts across all tables."""
        n_subjects  = await self.db.fetchscalar("SELECT COUNT(*) FROM subjects") or 0
        n_chapters  = await self.db.fetchscalar("SELECT COUNT(*) FROM chapters") or 0
        n_topics    = await self.db.fetchscalar("SELECT COUNT(*) FROM topics")   or 0
        n_questions = await self.db.fetchscalar("SELECT COUNT(*) FROM questions") or 0
        total_size  = await self.db.fetchscalar(
            "SELECT COALESCE(SUM(file_size), 0) FROM questions"
        ) or 0
        return {
            "subjects":  n_subjects,
            "chapters":  n_chapters,
            "topics":    n_topics,
            "questions": n_questions,
            "total_size_bytes": total_size,
        }
