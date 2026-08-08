from __future__ import annotations

import os
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_RUNTIME_DIRECTORY = tempfile.TemporaryDirectory(prefix="card-reader-integration-tests-")
RUNTIME_ROOT = Path(_RUNTIME_DIRECTORY.name)


def configure_test_environment() -> Path:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["CARD_READER_APP_DATA_DIR"] = str(RUNTIME_ROOT)
    os.environ["CARD_READER_ENV"] = "test"
    os.environ["DJANGO_SETTINGS_MODULE"] = "card_reader_api.project.test_settings"
    return RUNTIME_ROOT


def cleanup_test_environment() -> None:
    _RUNTIME_DIRECTORY.cleanup()
