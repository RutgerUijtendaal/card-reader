from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = REPO_ROOT / "services" / "integration" / ".runtime"


def configure_test_environment() -> Path:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["CARD_READER_APP_DATA_DIR"] = str(RUNTIME_ROOT)
    os.environ["CARD_READER_ENV"] = "test"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_api.project.settings")
    return RUNTIME_ROOT
