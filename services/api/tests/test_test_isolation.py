from __future__ import annotations

from pathlib import Path

from card_reader_core.models import Template, WorkerActivity, WorkerHeartbeat, now_utc

_PROBE_WORKER_KEY = "test-isolation-probe"
_PROBE_FILE_NAME = "test-isolation-probe.txt"


def test_isolation_probe_creates_database_and_file_state(test_storage_root: Path) -> None:
    now = now_utc()
    WorkerHeartbeat.objects.create(
        worker_key=_PROBE_WORKER_KEY,
        display_name="Isolation probe",
        activity=WorkerActivity.idle,
        started_at=now,
        last_heartbeat_at=now,
    )
    (test_storage_root / _PROBE_FILE_NAME).write_text("created by prior test", encoding="utf-8")

    assert WorkerHeartbeat.objects.filter(worker_key=_PROBE_WORKER_KEY).exists()
    assert (test_storage_root / _PROBE_FILE_NAME).exists()


def test_isolation_probe_starts_from_immutable_seed_baseline(test_storage_root: Path) -> None:
    assert not WorkerHeartbeat.objects.filter(worker_key=_PROBE_WORKER_KEY).exists()
    assert not (test_storage_root / _PROBE_FILE_NAME).exists()
    assert Template.objects.filter(key="mtg-like-v1").exists()
