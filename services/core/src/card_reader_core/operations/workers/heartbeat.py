from __future__ import annotations

import logging
from collections.abc import Callable
from threading import Event, Thread

from django.db import close_old_connections

from card_reader_core.models import WorkerActivity
from card_reader_core.repositories.worker_heartbeats import (
    heartbeat_worker,
    register_worker,
    stop_worker,
    update_worker_activity,
)
from card_reader_core.models.base import uuid_str


class WorkerHeartbeatSession:
    def __init__(
        self,
        *,
        worker_key: str,
        display_name: str,
        logger: logging.Logger,
        interval_seconds: float,
    ) -> None:
        self._worker_key = worker_key
        self._display_name = display_name
        self._logger = logger
        self._interval_seconds = max(1.0, interval_seconds)
        self._instance_id = uuid_str()
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        self._report(
            "register",
            lambda: register_worker(
                instance_id=self._instance_id,
                worker_key=self._worker_key,
                display_name=self._display_name,
            ),
        )
        self._thread = Thread(
            target=self._heartbeat_loop,
            name=f"{self._worker_key}-heartbeat",
            daemon=True,
        )
        self._thread.start()

    def mark_busy(self, work_id: str) -> None:
        self._report(
            "mark busy",
            lambda: update_worker_activity(
                instance_id=self._instance_id,
                activity=WorkerActivity.busy,
                current_work_id=work_id,
            ),
        )

    def mark_idle(self) -> None:
        self._report(
            "mark idle",
            lambda: update_worker_activity(
                instance_id=self._instance_id,
                activity=WorkerActivity.idle,
                current_work_id=None,
            ),
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=min(2.0, self._interval_seconds))
        self._report("stop", lambda: stop_worker(instance_id=self._instance_id))

    def _heartbeat_loop(self) -> None:
        close_old_connections()
        try:
            while not self._stop_event.wait(self._interval_seconds):
                self._report(
                    "heartbeat",
                    lambda: heartbeat_worker(instance_id=self._instance_id),
                )
        finally:
            close_old_connections()

    def _report(self, operation: str, callback: Callable[[], object]) -> None:
        try:
            callback()
        except Exception:
            self._logger.warning(
                "Worker heartbeat reporting failed. worker=%s operation=%s",
                self._worker_key,
                operation,
                exc_info=True,
            )
