from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from typing import Any

from ..settings import settings


def _resolve_database_path() -> Path:
    configured_path = settings.database_path
    if configured_path.is_absolute():
        return configured_path
    return settings.storage_root_dir / configured_path


DATABASE_PATH = _resolve_database_path()


def initialize_database() -> None:
    settings.storage_root_dir.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    settings.image_store_dir.mkdir(parents=True, exist_ok=True)


def get_session() -> Any:
    return nullcontext(None)
