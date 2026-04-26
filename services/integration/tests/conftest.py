from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

TEST_STORAGE_ROOT = Path(tempfile.mkdtemp(prefix="card-reader-integration-tests-"))
os.environ["CARD_READER_APP_DATA_DIR"] = str(TEST_STORAGE_ROOT)
os.environ["CARD_READER_ENV"] = "test"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_api.project.settings")

import django  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connections  # noqa: E402

django.setup()


@pytest.fixture(autouse=True)
def reset_db() -> None:
    from card_reader_core.database.connection import DATABASE_PATH, initialize_database
    from card_reader_api.seeds import run_registered_seeds

    connections.close_all()
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    initialize_database()
    call_command("migrate", interactive=False, verbosity=0)
    run_registered_seeds(force=False)
