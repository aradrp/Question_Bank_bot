"""
config.py – Application-level configuration loaded from environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class Config:
    # ── Bot ──────────────────────────────────────────────────────────────────
    BOT_TOKEN: str = ""
    ADMIN_IDS: List[int] = field(default_factory=list)

    # ── Storage paths ────────────────────────────────────────────────────────
    UPLOADS_DIR: str = "uploads"
    LOGS_DIR: str = "logs"
    DB_PATH: str = "database/question_bank.db"

    # ── File limits ──────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 50

    # ── UI ───────────────────────────────────────────────────────────────────
    ITEMS_PER_PAGE: int = 8

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_MAX_BYTES: int = 10 * 1024 * 1024   # 10 MB per log file
    LOG_BACKUP_COUNT: int = 5

    # ── Derived properties ───────────────────────────────────────────────────
    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def uploads_path(self) -> Path:
        return Path(self.UPLOADS_DIR)

    @property
    def db_path(self) -> Path:
        return Path(self.DB_PATH)

    @property
    def logs_path(self) -> Path:
        return Path(self.LOGS_DIR)


def load_config() -> Config:
    """Load and validate configuration from environment variables."""
    raw_ids = os.getenv("ADMIN_IDS", "")
    admin_ids: List[int] = []
    for part in raw_ids.split(","):
        part = part.strip()
        if part.isdigit():
            admin_ids.append(int(part))

    return Config(
        BOT_TOKEN=os.getenv("BOT_TOKEN", ""),
        ADMIN_IDS=admin_ids,
        UPLOADS_DIR=os.getenv("UPLOADS_DIR", "uploads"),
        LOGS_DIR=os.getenv("LOGS_DIR", "logs"),
        DB_PATH=os.getenv("DB_PATH", "database/question_bank.db"),
        MAX_FILE_SIZE_MB=int(os.getenv("MAX_FILE_SIZE_MB", "50")),
        ITEMS_PER_PAGE=int(os.getenv("ITEMS_PER_PAGE", "8")),
    )
