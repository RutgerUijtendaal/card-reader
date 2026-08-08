from __future__ import annotations

import logging

from django.db import OperationalError

from card_reader_core.database.connection import SQLITE_DATABASE_TIMEOUT_SECONDS
from card_reader_core.models import WorkerActivity
from card_reader_core.operations.workers import heartbeat as heartbeat_module
from card_reader_core.operations.workers.heartbeat import (
    DEFAULT_WORKER_HEARTBEAT_INTERVAL_SECONDS,
    WORKER_HEARTBEAT_STALE_AFTER,
    WorkerHeartbeatSession,
)


class _FakeThread:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def start(self) -> None:
        pass

    def join(self, timeout: float | None = None) -> None:
        del timeout


def test_worker_stale_window_exceeds_scheduled_interval_and_database_timeout() -> None:
    minimum_window = (
        DEFAULT_WORKER_HEARTBEAT_INTERVAL_SECONDS + SQLITE_DATABASE_TIMEOUT_SECONDS
    )

    assert WORKER_HEARTBEAT_STALE_AFTER.total_seconds() > minimum_window


def test_worker_registration_retries_before_later_activity(monkeypatch) -> None:
    registration_attempts = 0
    activity_updates: list[tuple[WorkerActivity, str | None]] = []

    def register(**_kwargs: object) -> object:
        nonlocal registration_attempts
        registration_attempts += 1
        if registration_attempts == 1:
            raise OperationalError("database is locked")
        return object()

    def update_activity(
        *, instance_id: str, activity: WorkerActivity, current_work_id: str | None
    ) -> None:
        del instance_id
        activity_updates.append((activity, current_work_id))

    monkeypatch.setattr(heartbeat_module, "Thread", _FakeThread)
    monkeypatch.setattr(heartbeat_module, "register_worker", register)
    monkeypatch.setattr(heartbeat_module, "update_worker_activity", update_activity)

    session = WorkerHeartbeatSession(
        worker_key="test-worker",
        display_name="Test worker",
        logger=logging.getLogger(__name__),
        interval_seconds=5,
    )

    session.start()
    session.mark_busy("work-1")

    assert registration_attempts == 0
    assert activity_updates == []

    session._report_status()
    session._report_status()

    assert registration_attempts == 2
    assert activity_updates == [(WorkerActivity.busy, "work-1")]


def test_worker_activity_updates_only_on_successful_transitions(monkeypatch) -> None:
    activity_updates: list[tuple[WorkerActivity, str | None]] = []

    def update_activity(
        *, instance_id: str, activity: WorkerActivity, current_work_id: str | None
    ) -> None:
        del instance_id
        activity_updates.append((activity, current_work_id))

    monkeypatch.setattr(heartbeat_module, "Thread", _FakeThread)
    monkeypatch.setattr(heartbeat_module, "register_worker", lambda **_kwargs: object())
    monkeypatch.setattr(heartbeat_module, "update_worker_activity", update_activity)

    session = WorkerHeartbeatSession(
        worker_key="test-worker",
        display_name="Test worker",
        logger=logging.getLogger(__name__),
        interval_seconds=5,
    )

    session.start()
    session._report_status()
    session.mark_idle()
    session.mark_idle()
    session.mark_busy("work-1")
    session.mark_busy("work-1")
    session._report_status()
    session.mark_idle()
    session.mark_idle()
    session._report_status()

    assert activity_updates == [
        (WorkerActivity.busy, "work-1"),
        (WorkerActivity.idle, None),
    ]


def test_worker_heartbeat_retries_failed_activity_transition(monkeypatch) -> None:
    activity_updates: list[tuple[WorkerActivity, str | None]] = []
    heartbeat_updates: list[str] = []

    def update_activity(
        *, instance_id: str, activity: WorkerActivity, current_work_id: str | None
    ) -> None:
        del instance_id
        activity_updates.append((activity, current_work_id))
        if len(activity_updates) == 1:
            raise OperationalError("database is locked")

    monkeypatch.setattr(heartbeat_module, "Thread", _FakeThread)
    monkeypatch.setattr(heartbeat_module, "register_worker", lambda **_kwargs: object())
    monkeypatch.setattr(heartbeat_module, "update_worker_activity", update_activity)
    monkeypatch.setattr(
        heartbeat_module,
        "heartbeat_worker",
        lambda *, instance_id: heartbeat_updates.append(instance_id),
    )

    session = WorkerHeartbeatSession(
        worker_key="test-worker",
        display_name="Test worker",
        logger=logging.getLogger(__name__),
        interval_seconds=5,
    )

    session.start()
    session._report_status()
    session.mark_busy("work-1")
    session._report_status()
    session._report_status()
    session._report_status()

    assert activity_updates == [
        (WorkerActivity.busy, "work-1"),
        (WorkerActivity.busy, "work-1"),
    ]
    assert len(heartbeat_updates) == 1


def test_worker_public_lifecycle_never_writes_on_calling_thread(monkeypatch) -> None:
    writes: list[str] = []

    monkeypatch.setattr(heartbeat_module, "Thread", _FakeThread)
    monkeypatch.setattr(
        heartbeat_module,
        "register_worker",
        lambda **_kwargs: writes.append("register"),
    )
    monkeypatch.setattr(
        heartbeat_module,
        "update_worker_activity",
        lambda **_kwargs: writes.append("activity"),
    )
    monkeypatch.setattr(
        heartbeat_module,
        "stop_worker",
        lambda **_kwargs: writes.append("stop"),
    )

    session = WorkerHeartbeatSession(
        worker_key="test-worker",
        display_name="Test worker",
        logger=logging.getLogger(__name__),
        interval_seconds=5,
    )

    session.start()
    session.mark_busy("work-1")
    session.mark_idle()
    session.stop()

    assert writes == []
