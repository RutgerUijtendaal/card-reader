from __future__ import annotations

import pytest
from django.db import OperationalError

from card_reader_core.config.settings import settings
from card_reader_core.database import retry as retry_module
from card_reader_core.models import (
    Card,
    CardVersion,
    CardVersionImage,
    ImportJob,
    ImportJobItem,
    ImportJobStatus,
    ParseResult,
    Template,
)
from card_reader_core.repositories.cards import save_parsed_card
from card_reader_core.repositories.cards import writes as card_writes
from card_reader_core.storage import build_storage_relative_path


def test_import_save_retries_the_complete_transaction_after_sqlite_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = settings.storage_root_dir / "uploads" / "retry-card.webp"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"retry-card-image")
    source_file = build_storage_relative_path("uploads", source_path.name)
    job = ImportJob.objects.create(
        source_path=source_file,
        template=Template.objects.get(key="mtg-like-v1"),
        total_items=1,
    )
    item = ImportJobItem.objects.create(
        job=job,
        source_file=source_file,
        status=ImportJobStatus.running,
    )
    original_create_version = card_writes.create_parsed_card_version
    attempts = 0

    def create_version_then_contend(**kwargs: object) -> CardVersion:
        nonlocal attempts
        attempts += 1
        version = original_create_version(**kwargs)
        if attempts == 1:
            raise OperationalError("database is locked")
        return version

    monkeypatch.setattr(card_writes, "create_parsed_card_version", create_version_then_contend)
    monkeypatch.setattr(retry_module.time, "sleep", lambda _delay: None)

    version = save_parsed_card(
        item=item,
        template_id="mtg-like-v1",
        checksum="retry-card-checksum",
        normalized_fields={
            "name": "Retry Card",
            "type_line": "Equipment",
            "mana_cost": "1",
            "rules_text": "Rules",
            "rules_text_raw": "Rules",
            "rules_text_enriched": "Rules",
        },
        confidence={"overall": 0.9},
        raw_ocr={"source": "retry-test"},
        reparse_existing=False,
    )

    item.refresh_from_db()
    assert attempts == 2
    assert item.status == ImportJobStatus.completed
    assert item.target_card_version_id == version.id
    assert Card.objects.filter(key="retry-card").count() == 1
    assert CardVersion.objects.filter(card=version.card).count() == 1
    assert CardVersionImage.objects.filter(card_version=version).count() == 1
    assert ParseResult.objects.filter(card_version=version).count() == 1
