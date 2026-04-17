from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from card_reader_api.infrastructure.models import Card
from card_reader_api.settings import settings

def _resolve_database_path() -> Path:
    configured_path = settings.database_path
    if configured_path.is_absolute():
        return configured_path
    return settings.storage_root_dir / configured_path


DATABASE_PATH = _resolve_database_path()
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def initialize_database() -> None:
    settings.storage_root_dir.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    settings.image_store_dir.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS card_search USING fts5(
              card_id UNINDEXED,
              name,
              type_line,
              rules_text,
              mana_cost
            )
            """
        )


def get_session() -> Session:
    return Session(engine)
