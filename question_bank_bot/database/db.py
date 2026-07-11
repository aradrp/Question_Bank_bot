"""
database/db.py – Async SQLite wrapper using aiosqlite.

Keeps a single WAL-mode connection for the life of the process.
All reads are concurrent; writes are serialised by SQLite itself.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Sequence

import aiosqlite

logger = logging.getLogger(__name__)

# DDL executed once on startup -------------------------------------------
_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS subjects (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chapters (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    name       TEXT    NOT NULL COLLATE NOCASE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    UNIQUE (subject_id, name)
);

CREATE TABLE IF NOT EXISTS topics (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id INTEGER NOT NULL,
    name       TEXT    NOT NULL COLLATE NOCASE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    UNIQUE (chapter_id, name)
);

CREATE TABLE IF NOT EXISTS questions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id      INTEGER NOT NULL,
    file_name     TEXT    NOT NULL,
    file_path     TEXT    NOT NULL UNIQUE,
    original_name TEXT,
    upload_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_size     INTEGER DEFAULT 0,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admins (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common look-ups
CREATE INDEX IF NOT EXISTS idx_chapters_subject ON chapters(subject_id);
CREATE INDEX IF NOT EXISTS idx_topics_chapter   ON topics(chapter_id);
CREATE INDEX IF NOT EXISTS idx_questions_topic  ON questions(topic_id);
CREATE INDEX IF NOT EXISTS idx_admins_tgid      ON admins(telegram_id);
"""


class Database:
    """Thin async wrapper around a single aiosqlite connection."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open the database file (creating it if absent) and apply the schema."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        logger.info("Database connected: %s", self._db_path)

    async def disconnect(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

    async def init_tables(self) -> None:
        """Create all tables and indexes."""
        assert self._conn, "Call connect() first"
        await self._conn.executescript(_SCHEMA_SQL)
        await self._conn.commit()
        logger.info("Database schema initialised")

    # ── Low-level helpers ─────────────────────────────────────────────────────

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._conn

    async def execute(
        self, sql: str, params: Sequence[Any] = ()
    ) -> aiosqlite.Cursor:
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cur

    async def executemany(self, sql: str, params_seq: Sequence[Sequence[Any]]) -> None:
        await self.conn.executemany(sql, params_seq)
        await self.conn.commit()

    async def fetchone(
        self, sql: str, params: Sequence[Any] = ()
    ) -> Optional[aiosqlite.Row]:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchone()

    async def fetchall(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[aiosqlite.Row]:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchall()

    async def fetchscalar(
        self, sql: str, params: Sequence[Any] = ()
    ) -> Any:
        row = await self.fetchone(sql, params)
        return row[0] if row else None
