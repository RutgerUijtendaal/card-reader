from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

TEST_STORAGE_ROOT = Path(tempfile.mkdtemp(prefix="card-reader-integration-tests-"))
os.environ["CARD_READER_APP_DATA_DIR"] = str(TEST_STORAGE_ROOT)
os.environ["CARD_READER_ENV"] = "test"


@pytest.fixture(autouse=True)
def reset_db() -> None:
    from card_reader_core.database.connection import DATABASE_PATH, engine, initialize_database
    from card_reader_api.database_migrations import run_migrations_to_head
    from card_reader_api.seeds import run_registered_seeds

    engine.dispose()
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    initialize_database()
    run_migrations_to_head()
    run_registered_seeds(force=False)
