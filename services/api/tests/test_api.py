from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_STORAGE_ROOT = Path(tempfile.mkdtemp(prefix="card-reader-api-tests-"))
os.environ["CARD_READER_APP_DATA_DIR"] = str(TEST_STORAGE_ROOT)
os.environ["CARD_READER_ENV"] = "test"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_api.project.settings")

import django  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.test import Client  # noqa: E402

django.setup()
call_command("migrate", interactive=False, verbosity=0)
call_command("seed_defaults", verbosity=0)


def test_health() -> None:
    response = Client(HTTP_HOST="localhost").get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_import_upload_rejects_unknown_template() -> None:
    response = Client(HTTP_HOST="localhost").post(
        "/imports/upload",
        data={
            "template_id": "unknown-template",
            "options_json": "{}",
            "files": SimpleUploadedFile("card.png", b"fake-image-content", content_type="image/png"),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown template_id 'unknown-template'"


def test_create_import_upload_rejects_unsupported_files() -> None:
    response = Client(HTTP_HOST="localhost").post(
        "/imports/upload",
        data={"template_id": "mtg-like-v1", "options_json": "{}"},
    )
    assert response.status_code == 400
