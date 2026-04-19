from pathlib import Path

from sqlmodel import Session, create_engine

from ..settings import settings


def _resolve_database_path() -> Path:
    configured_path = settings.database_path
    if configured_path.is_absolute():
        return configured_path
    return settings.storage_root_dir / configured_path


DATABASE_PATH = _resolve_database_path()
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def initialize_database() -> None:
    settings.storage_root_dir.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    settings.image_store_dir.mkdir(parents=True, exist_ok=True)


def get_session() -> Session:
    return Session(engine)


