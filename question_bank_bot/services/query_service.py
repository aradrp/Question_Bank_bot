"""
services/query_service.py – Higher-level queries and formatted output helpers.
"""
from __future__ import annotations

import logging

from database.repository import Repository
from services.file_service import FileService

logger = logging.getLogger(__name__)


def fmt_bytes(n: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


class QueryService:
    def __init__(self, repo: Repository, file_svc: FileService) -> None:
        self.repo = repo
        self.file_svc = file_svc

    async def get_stats_text(self) -> str:
        stats = await self.repo.get_statistics()
        disk = self.file_svc.disk_usage()
        uploads_size = self.file_svc.uploads_size()
        zip_count = self.file_svc.count_zip_files()

        lines = [
            "📊 <b>Bot Statistics</b>\n",
            f"📚 Subjects:   <b>{stats['subjects']}</b>",
            f"📂 Chapters:   <b>{stats['chapters']}</b>",
            f"📋 Topics:     <b>{stats['topics']}</b>",
            f"📄 PDFs:       <b>{stats['questions']}</b>",
            f"📦 ZIP files:  <b>{zip_count}</b>",
            "",
            f"💾 PDFs size:  <b>{fmt_bytes(uploads_size)}</b>",
            f"🖥 Disk used:  <b>{fmt_bytes(disk['used'])}</b> / "
            f"<b>{fmt_bytes(disk['total'])}</b> ({disk['percent']:.1f}%)",
            f"🟢 Disk free:  <b>{fmt_bytes(disk['free'])}</b>",
        ]
        return "\n".join(lines)
