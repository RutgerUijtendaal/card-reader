from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from database.connection import DATABASE_URL

logger = logging.getLogger(__name__)


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(meipass)
    return Path(__file__).resolve().parents[1]


def run_migrations_to_head() -> None:
    root = _resource_root()
    script_location = root / "alembic"
    if not script_location.exists():
        raise FileNotFoundError(f"Alembic script location not found: {script_location}")

    config = Config()
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

    logger.info("Running Alembic migrations to head. script_location=%s", script_location)
    command.upgrade(config, "head")
    logger.info("Alembic migrations completed")

