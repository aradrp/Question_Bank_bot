"""
bot.py – Application entry point.

Start order
───────────
1. Load config from environment variables
2. Configure rotating-file + console logging
3. Open SQLite database and run migrations
4. Seed ADMIN_IDS into the admins table
5. Build the Dispatcher with all routers attached
6. Start long-polling
"""
from __future__ import annotations

import asyncio
import logging
import logging.handlers
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from database.db import Database
from database.repository import Repository
from handlers import admin, common, start, user
from services.file_service import FileService
from services.query_service import QueryService
from services.zip_service import ZipService


# ─────────────────────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging(logs_dir: str, max_bytes: int, backup_count: int) -> None:
    Path(logs_dir).mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler
    fh = logging.handlers.RotatingFileHandler(
        filename=Path(logs_dir) / "bot.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(fh)
    root.addHandler(ch)

    # Silence noisy third-party loggers
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────────────────────
# Startup / shutdown hooks
# ─────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, db: Database, repo: Repository, config) -> None:
    await db.connect()
    await db.init_tables()

    # Seed admin IDs from config into the database
    for admin_id in config.ADMIN_IDS:
        await repo.add_admin(admin_id)
        logger.info("Admin seeded: %s", admin_id)

    me = await bot.get_me()
    logger.info("Bot started: @%s (id=%s)", me.username, me.id)


async def on_shutdown(db: Database) -> None:
    await db.disconnect()
    logger.info("Bot stopped.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    config = load_config()

    if not config.BOT_TOKEN:
        print("ERROR: BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    setup_logging(config.LOGS_DIR, config.LOG_MAX_BYTES, config.LOG_BACKUP_COUNT)
    logger.info("Starting Question Bank Bot…")

    # Ensure directories exist
    config.uploads_path.mkdir(parents=True, exist_ok=True)
    config.logs_path.mkdir(parents=True, exist_ok=True)
    config.db_path.parent.mkdir(parents=True, exist_ok=True)

    # Services
    db        = Database(str(config.db_path))
    repo      = Repository(db)
    file_svc  = FileService(config.UPLOADS_DIR)
    zip_svc   = ZipService(config.UPLOADS_DIR)
    query_svc = QueryService(repo, file_svc)

    # Bot & Dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Inject dependencies via workflow_data (available in every handler)
    dp.workflow_data.update(
        config=config,
        db=db,
        repo=repo,
        file_svc=file_svc,
        zip_svc=zip_svc,
        query_svc=query_svc,
    )

    # Register routers (ORDER MATTERS – admin before common catch-all)
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.include_router(common.router)

    # Lifecycle
    await on_startup(bot, db, repo, config)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await on_shutdown(db)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
