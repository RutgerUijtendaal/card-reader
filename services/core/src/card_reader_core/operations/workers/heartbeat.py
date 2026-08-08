from __future__ import annotations

import logging
from collections.abc import Callable
from threading import Event, Lock, Thread

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
        self._registered = False
        self._registration_lock = Lock()
        self._activity_lock = Lock()
        self._desired_activity: tuple[WorkerActivity, str | None] = (WorkerActivity.idle, None)
        self._reported_activity: tuple[WorkerActivity, str | None] | None = None

    def start(self) -> None:
        self._ensure_registered()
        self._thread = Thread(
            target=self._heartbeat_loop,
            name=f"{self._worker_key}-heartbeat",
            daemon=True,
        )
        self._thread.start()

    def mark_busy(self, work_id: str) -> None:
        self._report_activity(
            "mark busy",
            activity=WorkerActivity.busy,
            current_work_id=work_id,
        )

    def mark_idle(self) -> None:
        self._report_activity(
            "mark idle",
            activity=WorkerActivity.idle,
            current_work_id=None,
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=min(2.0, self._interval_seconds))
        self._report_registered("stop", lambda: stop_worker(instance_id=self._instance_id))

    def _heartbeat_loop(self) -> None:
        close_old_connections()
        try:
            while not self._stop_event.wait(self._interval_seconds):
                self._report_heartbeat()
        finally:
            close_old_connections()

    def _report_heartbeat(self) -> None:
        if not self._ensure_registered():
            return
        with self._activity_lock:
            if self._reported_activity != self._desired_activity:
                self._report_desired_activity_locked("retry activity")
            else:
                self._report(
                    "heartbeat",
                    lambda: heartbeat_worker(instance_id=self._instance_id),
                )

    def _ensure_registered(self) -> bool:
        if self._registered:
            return True
        with self._registration_lock:
            if self._registered:
                return True
            registered = self._report(
                "register",
                lambda: register_worker(
                    instance_id=self._instance_id,
                    worker_key=self._worker_key,
                    display_name=self._display_name,
                ),
            )
            if registered:
                self._registered = True
                with self._activity_lock:
                    self._reported_activity = (WorkerActivity.idle, None)
            return self._registered

    def _report_activity(
        self,
        operation: str,
        *,
        activity: WorkerActivity,
        current_work_id: str | None,
    ) -> None:
        with self._activity_lock:
            self._desired_activity = (activity, current_work_id)
        if not self._ensure_registered():
            return
        with self._activity_lock:
            self._report_desired_activity_locked(operation)

    def _report_desired_activity_locked(self, operation: str) -> None:
        if self._reported_activity == self._desired_activity:
            return
        activity, current_work_id = self._desired_activity
        reported = self._report(
            operation,
            lambda: update_worker_activity(
                instance_id=self._instance_id,
                activity=activity,
                current_work_id=current_work_id,
            ),
        )
        if reported:
            self._reported_activity = self._desired_activity

    def _report_registered(self, operation: str, callback: Callable[[], object]) -> None:
        if self._ensure_registered():
            self._report(operation, callback)

    def _report(self, operation: str, callback: Callable[[], object]) -> bool:
        try:
            callback()
            return True
        except Exception:
            self._logger.warning(
                "Worker heartbeat reporting failed. worker=%s operation=%s",
                self._worker_key,
                operation,
                exc_info=True,
            )
            return False
