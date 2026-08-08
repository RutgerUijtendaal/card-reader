from __future__ import annotations

import logging

from django.db import OperationalError

from card_reader_core.models import WorkerActivity
from card_reader_core.operations.workers import heartbeat as heartbeat_module
from card_reader_core.operations.workers.heartbeat import WorkerHeartbeatSession


class _FakeThread:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def start(self) -> None:
        pass

    def join(self, timeout: float | None = None) -> None:
        del timeout


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
    session.mark_idle()
    session.mark_idle()
    session.mark_busy("work-1")
    session.mark_idle()
    session.mark_idle()

    assert activity_updates == [
        (WorkerActivity.busy, "work-1"),
        (WorkerActivity.idle, None),
    ]
