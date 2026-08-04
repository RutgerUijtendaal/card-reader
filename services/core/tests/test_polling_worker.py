from __future__ import annotations

import logging
from pathlib import Path

import pytest

from card_reader_core.operations.workers import (
    PollingWorker,
    PollingWorkerConfig,
    StopRequested,
    WorkerShutdownController,
)


def test_polling_worker_runs_shared_lifecycle_once(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_signal_handlers(monkeypatch)
    events: list[str] = []

    def claim_next() -> str:
        events.append("claim")
        return "work-1"

    def process(work: str, should_stop: StopRequested) -> None:
        assert should_stop() is False
        events.append(f"process:{work}")

    PollingWorker[str](
        config=PollingWorkerConfig(name="Test worker", interval_seconds=0.01, once=True),
        logger=logging.getLogger("test.polling-worker"),
        claim_next=claim_next,
        process=process,
        initialize=lambda: events.append("initialize"),
        recover=lambda: events.append("recover"),
        on_claimed=lambda work: events.append(f"claimed:{work}"),
        on_processed=lambda work: events.append(f"processed:{work}"),
    ).run()

    assert events == [
        "initialize",
        "recover",
        "claim",
        "claimed:work-1",
        "process:work-1",
        "processed:work-1",
    ]


def test_polling_worker_recovers_claim_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_signal_handlers(monkeypatch)
    recovery_count = 0

    def recover() -> None:
        nonlocal recovery_count
        recovery_count += 1

    def fail_to_claim() -> str | None:
        raise RuntimeError("database unavailable")

    PollingWorker[str](
        config=PollingWorkerConfig(name="Test worker", interval_seconds=0.01, once=True),
        logger=logging.getLogger("test.polling-worker"),
        claim_next=fail_to_claim,
        process=lambda _work, _should_stop: None,
        recover=recover,
    ).run()

    assert recovery_count == 2


def test_polling_worker_retries_startup_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _disable_signal_handlers(monkeypatch)
    attempts = 0
    events: list[str] = []
    marker = tmp_path / "stop"

    def initialize() -> None:
        nonlocal attempts
        attempts += 1
        events.append(f"initialize:{attempts}")
        if attempts == 1:
            raise RuntimeError("schema is not ready")

    def process(work: str, _should_stop: StopRequested) -> None:
        events.append(f"process:{work}")
        marker.touch()

    PollingWorker[str](
        config=PollingWorkerConfig(
            name="Test worker",
            interval_seconds=0,
            shutdown_marker=marker,
        ),
        logger=logging.getLogger("test.polling-worker"),
        claim_next=lambda: "work-1",
        process=process,
        initialize=initialize,
    ).run()

    assert events == ["initialize:1", "initialize:2", "process:work-1"]


def test_shutdown_controller_honors_marker_file(tmp_path: Path) -> None:
    marker = tmp_path / "stop"
    controller = WorkerShutdownController(
        worker_name="Test worker",
        logger=logging.getLogger("test.polling-worker"),
        marker_file=marker,
    )

    assert controller.should_stop() is False
    marker.touch()
    assert controller.should_stop() is True


def _disable_signal_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        WorkerShutdownController,
        "install_signal_handlers",
        lambda _controller: None,
    )
