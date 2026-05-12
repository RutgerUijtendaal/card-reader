from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_STORAGE_ROOT = Path(tempfile.mkdtemp(prefix="card-reader-api-tests-"))
os.environ["CARD_READER_APP_DATA_DIR"] = str(TEST_STORAGE_ROOT)
os.environ["CARD_READER_ENV"] = "test"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_api.project.settings")

import django  # noqa: E402
from card_reader_core.database.connection import initialize_database  # noqa: E402
from django.core.management import call_command  # noqa: E402

initialize_database()
django.setup()

call_command("migrate", interactive=False, verbosity=0)
call_command("seed_defaults", verbosity=0)
