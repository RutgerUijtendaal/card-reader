from __future__ import annotations

import os
from pathlib import Path
import tempfile

_TEST_DATABASE_DIRECTORY = tempfile.TemporaryDirectory(prefix="card-reader-django-tests-")
TEST_DATABASE_ROOT = Path(_TEST_DATABASE_DIRECTORY.name)

# These must be set before importing the shared settings singleton.
os.environ["CARD_READER_APP_DATA_DIR"] = str(TEST_DATABASE_ROOT)
os.environ["CARD_READER_ENV"] = "test"

from card_reader_core.config import django as core_django_settings  # noqa: E402

from .settings import *  # noqa: E402, F403

DATABASES = {
    "default": {
        **core_django_settings.DATABASES["default"],
        "TEST": {"NAME": str(TEST_DATABASE_ROOT / "card-reader-test.sqlite3")},
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
