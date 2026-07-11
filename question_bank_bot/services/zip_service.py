"""
services/zip_service.py – ZIP archive generation for question topics.

All ZIP I/O is offloaded to a thread-pool executor so that the asyncio
event loop is never blocked, even for archives that are gigabytes in size.
"""
from __future__ import annotations

import asyncio
import logging
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class ZipService:
    def __init__(self, uploads_dir: str, max_workers: int = 3) -> None:
        self.uploads_dir = Path(uploads_dir)
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="zip")

    # ── Path helpers ──────────────────────────────────────────────────────

    def zip_path(
        self,
        subject_name: str,
        chapter_name: str,
        topic_name: str,
    ) -> Path:
        """Return the canonical path for a topic's ZIP archive."""
        from services.file_service import FileService
        s = FileService.sanitize_name(subject_name)
        c = FileService.sanitize_name(chapter_name)
        t = FileService.sanitize_name(topic_name)
        return self.uploads_dir / s / c / t / f"{t}.zip"

    # ── Core operations ───────────────────────────────────────────────────

    async def create_zip(
        self,
        zip_target: Path,
        file_paths: List[str],
    ) -> bool:
        """
        Build a ZIP archive at *zip_target* containing all files in
        *file_paths*.  Runs in a thread so it never blocks the event loop.
        """
        if not file_paths:
            logger.debug("create_zip: no files provided for %s", zip_target)
            return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._sync_create_zip,
            zip_target,
            file_paths,
        )

    def _sync_create_zip(self, zip_target: Path, file_paths: List[str]) -> bool:
        existing = [p for p in file_paths if Path(p).is_file()]
        if not existing:
            logger.warning("_sync_create_zip: none of the source files exist")
            return False
        try:
            zip_target.parent.mkdir(parents=True, exist_ok=True)
            tmp = zip_target.with_suffix(".zip.tmp")
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                for fp in existing:
                    zf.write(fp, arcname=Path(fp).name)
            tmp.replace(zip_target)   # atomic rename
            logger.info(
                "ZIP created: %s (%d files, %.2f MB)",
                zip_target,
                len(existing),
                zip_target.stat().st_size / 1_048_576,
            )
            return True
        except Exception as exc:
            logger.error("ZIP creation failed for %s: %s", zip_target, exc)
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            return False

    async def delete_zip(self, zip_target: Path) -> bool:
        if zip_target.exists():
            zip_target.unlink()
            logger.info("ZIP deleted: %s", zip_target)
            return True
        return False

    async def regenerate_zip(
        self,
        subject_name: str,
        chapter_name: str,
        topic_name: str,
        file_paths: List[str],
    ) -> bool:
        """
        Delete the old ZIP (if any) and rebuild it.
        Called automatically on every upload and delete.
        """
        zp = self.zip_path(subject_name, chapter_name, topic_name)
        await self.delete_zip(zp)

        if not file_paths:
            logger.debug("regenerate_zip: no files remain; ZIP not recreated")
            return False

        return await self.create_zip(zp, file_paths)

    def zip_exists(
        self,
        subject_name: str,
        chapter_name: str,
        topic_name: str,
    ) -> bool:
        return self.zip_path(subject_name, chapter_name, topic_name).is_file()

    def zip_size_mb(
        self,
        subject_name: str,
        chapter_name: str,
        topic_name: str,
    ) -> float:
        p = self.zip_path(subject_name, chapter_name, topic_name)
        return p.stat().st_size / 1_048_576 if p.is_file() else 0.0
