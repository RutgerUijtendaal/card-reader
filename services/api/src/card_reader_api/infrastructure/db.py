from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from card_reader_api.infrastructure.models import Card
from card_reader_api.settings import settings

DATABASE_URL = f"sqlite:///{settings.database_path}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def initialize_database() -> None:
    settings.app_data_dir.mkdir(parents=True, exist_ok=True)
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