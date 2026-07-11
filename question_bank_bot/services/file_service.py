"""
services/file_service.py – All filesystem operations for uploaded PDFs.

Security notes
──────────────
• sanitize_name() strips characters that would allow path traversal.
• Files are always written under UPLOADS_DIR; absolute paths from user
  input are never used directly.
• Uniqueness is guaranteed via uuid4.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path

import aiofiles
import psutil

logger = logging.getLogger(__name__)

_UNSAFE_RE = re.compile(r"[^\w\s\-\.]")   # keep word chars, spaces, dashes, dots


class FileService:
    def __init__(self, uploads_dir: str) -> None:
        self.uploads_dir = Path(uploads_dir)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    # ── Naming helpers ────────────────────────────────────────────────────

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Convert a free-text name into a safe directory/file component."""
        name = name.strip()
        name = _UNSAFE_RE.sub("_", name)
        name = re.sub(r"_+", "_", name)        # collapse consecutive underscores
        name = name.strip("_. ")
        return name or "unnamed"

    def topic_dir(
        self,
        subject_name: str,
        chapter_name: str,
        topic_name: str,
    ) -> Path:
        return (
            self.uploads_dir
            / self.sanitize_name(subject_name)
            / self.sanitize_name(chapter_name)
            / self.sanitize_name(topic_name)
        )

    @staticmethod
    def unique_filename(original: str) -> str:
        """Return <uuid4>_<sanitized_original>.pdf."""
        stem = Path(original).stem
        stem_safe = FileService.sanitize_name(stem)[:80]
        return f"{uuid.uuid4().hex}_{stem_safe}.pdf"

    # ── Core operations ───────────────────────────────────────────────────

    async def save_pdf(
        self,
        file_bytes: bytes,
        subject_name: str,
        chapter_name: str,
        topic_name: str,
        original_name: str,
    ) -> tuple[str, str, int]:
        """
        Persist *file_bytes* to disk.

        Returns (file_name, file_path_str, file_size_bytes).
        """
        dir_path = self.topic_dir(subject_name, chapter_name, topic_name)
        dir_path.mkdir(parents=True, exist_ok=True)

        file_name = self.unique_filename(original_name)
        file_path = dir_path / file_name

        async with aiofiles.open(file_path, "wb") as fh:
            await fh.write(file_bytes)

        size = file_path.stat().st_size
        logger.info("Saved PDF: %s (%d bytes)", file_path, size)
        return file_name, str(file_path), size

    async def delete_file(self, file_path: str) -> bool:
        """Remove a file from disk; returns True if successful."""
        p = Path(file_path)
        if p.exists():
            p.unlink()
            logger.info("Deleted file: %s", file_path)
            return True
        logger.warning("delete_file: not found: %s", file_path)
        return False

    def file_exists(self, file_path: str) -> bool:
        return Path(file_path).is_file()

    # ── Disk usage ────────────────────────────────────────────────────────

    def disk_usage(self) -> dict:
        """Return free/total/used for the partition containing UPLOADS_DIR."""
        try:
            usage = psutil.disk_usage(str(self.uploads_dir))
            return {
                "total": usage.total,
                "used":  usage.used,
                "free":  usage.free,
                "percent": usage.percent,
            }
        except Exception as exc:
            logger.warning("disk_usage failed: %s", exc)
            return {"total": 0, "used": 0, "free": 0, "percent": 0}

    def uploads_size(self) -> int:
        """Return total bytes occupied by every file under uploads_dir."""
        total = 0
        for root, _, files in os.walk(self.uploads_dir):
            for fname in files:
                try:
                    total += os.path.getsize(os.path.join(root, fname))
                except OSError:
                    pass
        return total

    def count_zip_files(self) -> int:
        count = 0
        for root, _, files in os.walk(self.uploads_dir):
            count += sum(1 for f in files if f.endswith(".zip"))
        return count

    # ── Validation ────────────────────────────────────────────────────────

    @staticmethod
    def validate_pdf(file_bytes: bytes, original_name: str, max_bytes: int) -> str | None:
        """
        Perform basic PDF validation.
        Returns an error string, or None if the file is acceptable.
        """
        if len(file_bytes) > max_bytes:
            return (
                f"File too large ({len(file_bytes) // (1024*1024)} MB). "
                f"Maximum is {max_bytes // (1024*1024)} MB."
            )
        if not original_name.lower().endswith(".pdf"):
            return "Only PDF files are accepted."
        if not file_bytes.startswith(b"%PDF"):
            return "File does not appear to be a valid PDF (missing %PDF header)."
        return None
