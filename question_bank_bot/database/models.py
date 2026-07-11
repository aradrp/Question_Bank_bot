"""
database/models.py – Plain-Python data models (dataclasses) for every DB table.
These are used as return types from the Repository layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Subject:
    id: int
    name: str
    created_at: Optional[datetime] = None


@dataclass
class Chapter:
    id: int
    subject_id: int
    name: str
    created_at: Optional[datetime] = None


@dataclass
class Topic:
    id: int
    chapter_id: int
    name: str
    created_at: Optional[datetime] = None


@dataclass
class Question:
    id: int
    topic_id: int
    file_name: str
    file_path: str
    original_name: Optional[str] = None
    upload_date: Optional[datetime] = None
    file_size: int = 0


@dataclass
class Admin:
    id: int
    telegram_id: int
    added_at: Optional[datetime] = None
