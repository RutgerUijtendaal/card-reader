from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.db import connection
from PIL import Image

from card_reader_core.config.settings import settings
from card_reader_core.models import CardVersion, ImportJob, ImportJobItem, Template
from card_reader_core.repositories.import_jobs import (
    cancel_import_job,
    create_import_job_with_files,
    fetch_items_for_job,
    mark_job_item_running,
    requeue_running_import_jobs,
)
from card_reader_core.services.classification_rules import ClassificationRuleService
from card_reader_core.services.parser_jobs import ImportProcessorService

pytestmark = pytest.mark.django_db(transaction=True)


class ParserKilled(BaseException):
    """An abrupt exit bypasses the processor's ordinary exception handler."""


class StubParser:
    def __init__(self, *, killed: str | None = None, failed: str | None = None) -> None:
        self.killed = killed
        self.failed = failed
        self.calls: list[str] = []

    def parse(self, image_path: Path, template_id: str, **_: object) -> SimpleNamespace:
        # A process exit must not roll the claim/attempt back with its OCR work.
        assert not connection.in_atomic_block
        item = ImportJobItem.objects.get(source_file__endswith=image_path.name)
        assert item.status == "running"
        assert item.attempt_count >= 1
        self.calls.append(image_path.name)
        if image_path.name == self.killed:
            raise ParserKilled()
        if image_path.name == self.failed:
            raise ValueError("Invalid image")
        return SimpleNamespace(
            checksum=sha256(image_path.read_bytes()).hexdigest(),
            normalized_fields={
                "name": image_path.stem,
                "type_line": "",
                "mana_cost": "",
                "attack": "",
                "health": "",
                "rules_text": "",
            },
            confidence={"overall": 0.9},
            raw_ocr={},
            keyword_ids=[],
            tag_ids=[],
            type_ids=[],
            symbol_ids=[],
            tag_suggestions=[],
            type_suggestions=[],
        )


@pytest.fixture
def job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ImportJob:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    folder = settings.storage_root_dir / "uploads" / "attempts"
    folder.mkdir(parents=True)
    files = [folder / "first.png", folder / "second.png"]
    for path, color in zip(files, ["red", "blue"], strict=True):
        Image.new("RGB", (10, 10), color).save(path)
    template = Template.objects.create(key="retry-test", label="Retry test")
    return create_import_job_with_files(
        source_path=folder,
        template_id=template.key,
        options={},
        files=files,
        classification_rule_snapshot=ClassificationRuleService().build_snapshot(
            card_pool="player", include_roles=True, include_factions=True,
        ),
    )


def test_three_crashes_exhaust_one_item_and_remaining_cards_continue(job: ImportJob) -> None:
    for attempt in range(1, 4):
        parser = StubParser(killed="first.png")
        with pytest.raises(ParserKilled):
            ImportProcessorService(parser).process_job(job.id)
        first, second = fetch_items_for_job(job.id)
        assert (first.status, first.attempt_count) == ("running", attempt)
        assert (second.status, second.attempt_count) == ("queued", 0)
        assert requeue_running_import_jobs() == (1, 1)
        first.refresh_from_db()
        assert first.status == ("failed" if attempt == 3 else "queued")
        # Repeated recovery must not replenish or spend the attempt budget.
        assert requeue_running_import_jobs() == (0, 0)

    parser = StubParser()
    ImportProcessorService(parser).process_job(job.id)
    first, second = fetch_items_for_job(job.id)
    job.refresh_from_db()
    assert parser.calls == ["second.png"]
    assert (first.status, first.attempt_count) == ("failed", 3)
    assert "stopped after 3 attempts" in (first.error_message or "")
    assert (second.status, second.attempt_count) == ("completed", 1)
    assert (job.status, job.processed_items) == ("failed", 2)
    assert CardVersion.objects.count() == 1


def test_success_on_third_attempt_is_allowed(job: ImportJob) -> None:
    for _ in range(2):
        with pytest.raises(ParserKilled):
            ImportProcessorService(StubParser(killed="first.png")).process_job(job.id)
        requeue_running_import_jobs()
    ImportProcessorService(StubParser()).process_job(job.id)
    job.refresh_from_db()
    assert (job.status, job.processed_items) == ("completed", 2)
    assert [item.attempt_count for item in fetch_items_for_job(job.id)] == [3, 1]


def test_caught_error_is_not_retried_and_survives_later_worker_exit(job: ImportJob) -> None:
    with pytest.raises(ParserKilled):
        ImportProcessorService(
            StubParser(failed="first.png", killed="second.png")
        ).process_job(job.id)
    requeue_running_import_jobs()
    parser = StubParser()
    ImportProcessorService(parser).process_job(job.id)
    job.refresh_from_db()
    assert parser.calls == ["second.png"]
    assert (job.status, job.processed_items) == ("failed", 2)
    first, second = fetch_items_for_job(job.id)
    assert first.error_message == "Invalid image"
    assert [first.attempt_count, second.attempt_count] == [1, 2]


def test_shutdown_after_failure_keeps_remaining_work_queued(job: ImportJob) -> None:
    parser = StubParser(failed="first.png")
    ImportProcessorService(parser).process_job(job.id, should_stop=lambda: bool(parser.calls))
    job.refresh_from_db()
    assert (job.status, job.processed_items) == ("queued", 1)
    assert [item.attempt_count for item in fetch_items_for_job(job.id)] == [1, 0]
    ImportProcessorService(StubParser()).process_job(job.id)
    job.refresh_from_db()
    assert (job.status, job.processed_items) == ("failed", 2)


def test_shutdown_before_claim_does_not_consume_attempts(job: ImportJob) -> None:
    parser = StubParser()
    ImportProcessorService(parser).process_job(job.id, should_stop=lambda: True)
    job.refresh_from_db()
    assert (job.status, job.processed_items) == ("queued", 0)
    assert parser.calls == []
    assert [item.attempt_count for item in fetch_items_for_job(job.id)] == [0, 0]


@pytest.mark.parametrize("attempts", [0, 2, 3])
def test_cancellation_takes_precedence_over_recovery(job: ImportJob, attempts: int) -> None:
    first, second = fetch_items_for_job(job.id)
    ImportJob.objects.filter(id=job.id).update(status="running")
    ImportJobItem.objects.filter(id=first.id).update(status="running", attempt_count=attempts)
    cancel_import_job(job.id)
    requeue_running_import_jobs()
    first.refresh_from_db()
    second.refresh_from_db()
    job.refresh_from_db()
    assert (job.status, job.processed_items) == ("cancelled", 2)
    assert first.status == second.status == "cancelled"
    assert first.attempt_count == attempts
    assert first.error_message is None


def test_claim_rejects_duplicate_and_exhausted_queued_items(job: ImportJob) -> None:
    first, second = fetch_items_for_job(job.id)
    stale = ImportJobItem.objects.get(id=first.id)
    assert mark_job_item_running(first)
    assert not mark_job_item_running(stale)
    assert stale.attempt_count == 1
    ImportJobItem.objects.filter(id=second.id).update(attempt_count=3)
    assert not mark_job_item_running(second)
    assert (second.status, second.attempt_count) == ("failed", 3)


def test_recovery_finalizes_exhausted_last_item_without_more_parsing(job: ImportJob) -> None:
    first, second = fetch_items_for_job(job.id)
    ImportJob.objects.filter(id=job.id).update(status="running")
    ImportJobItem.objects.filter(id=first.id).update(status="completed", attempt_count=1)
    ImportJobItem.objects.filter(id=second.id).update(status="running", attempt_count=3)
    assert requeue_running_import_jobs() == (1, 1)
    job.refresh_from_db()
    assert (job.status, job.processed_items) == ("failed", 2)
    first.refresh_from_db()
    assert (first.status, first.attempt_count) == ("completed", 1)


def test_exit_after_saved_success_does_not_replay_card(
    job: ImportJob, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def kill_after_save(*_: object) -> None:
        raise ParserKilled()

    processor = ImportProcessorService(StubParser())
    monkeypatch.setattr(processor, "_log_item_processed", kill_after_save)
    with pytest.raises(ParserKilled):
        processor.process_job(job.id)
    assert CardVersion.objects.count() == 1
    assert requeue_running_import_jobs() == (1, 0)
    parser = StubParser()
    ImportProcessorService(parser).process_job(job.id)
    job.refresh_from_db()
    assert parser.calls == ["second.png"]
    assert (job.status, job.processed_items) == ("completed", 2)
    assert CardVersion.objects.count() == 2
    assert [item.attempt_count for item in fetch_items_for_job(job.id)] == [1, 1]
