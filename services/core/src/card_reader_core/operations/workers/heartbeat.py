from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta
from threading import Event, Lock, Thread

from django.db import close_old_connections

from card_reader_core.database.connection import SQLITE_DATABASE_TIMEOUT_SECONDS
from card_reader_core.models import WorkerActivity
from card_reader_core.repositories.worker_heartbeats import (
    heartbeat_worker,
    register_worker,
    stop_worker,
    update_worker_activity,
)
from card_reader_core.models.base import uuid_str

DEFAULT_WORKER_HEARTBEAT_INTERVAL_SECONDS = 10.0
# Cover a scheduled interval, SQLite's full lock wait, and two intervals of scheduling margin.
WORKER_HEARTBEAT_STALE_AFTER = timedelta(
    seconds=SQLITE_DATABASE_TIMEOUT_SECONDS + (3 * DEFAULT_WORKER_HEARTBEAT_INTERVAL_SECONDS)
)


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
        self._wake_event = Event()
        self._thread: Thread | None = None
        self._registered = False
        self._activity_lock = Lock()
        self._desired_activity: tuple[WorkerActivity, str | None] = (WorkerActivity.idle, None)
        self._reported_activity: tuple[WorkerActivity, str | None] | None = None

    def start(self) -> None:
        self._thread = Thread(
            target=self._heartbeat_loop,
            name=f"{self._worker_key}-heartbeat",
            daemon=True,
        )
        self._thread.start()

    def mark_busy(self, work_id: str) -> None:
        self._set_desired_activity(
            activity=WorkerActivity.busy,
            current_work_id=work_id,
        )

    def mark_idle(self) -> None:
        self._set_desired_activity(
            activity=WorkerActivity.idle,
            current_work_id=None,
        )

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread is not None:
            self._thread.join(timeout=min(2.0, self._interval_seconds))

    def _heartbeat_loop(self) -> None:
        close_old_connections()
        try:
            while not self._stop_event.is_set():
                self._report_status()
                self._wake_event.wait(self._interval_seconds)
                self._wake_event.clear()
            self._report_stop()
        finally:
            close_old_connections()

    def _report_status(self) -> None:
        was_registered = self._registered
        if not self._ensure_registered():
            return
        desired_activity = self._desired_activity_snapshot()
        if self._reported_activity != desired_activity:
            activity, current_work_id = desired_activity

            def report_activity() -> None:
                update_worker_activity(
                    instance_id=self._instance_id,
                    activity=activity,
                    current_work_id=current_work_id,
                )

            reported = self._report(
                "activity",
                report_activity,
            )
            if reported:
                self._reported_activity = desired_activity
            return
        if not was_registered:
            return
        self._report("heartbeat", self._send_heartbeat)

    def _ensure_registered(self) -> bool:
        if self._registered:
            return True
        registered = self._report("register", self._register_worker)
        if registered:
            self._registered = True
            self._reported_activity = (WorkerActivity.idle, None)
        return self._registered

    def _set_desired_activity(
        self,
        *,
        activity: WorkerActivity,
        current_work_id: str | None,
    ) -> None:
        desired_activity = (activity, current_work_id)
        with self._activity_lock:
            if self._desired_activity == desired_activity:
                return
            self._desired_activity = desired_activity
        self._wake_event.set()

    def _desired_activity_snapshot(self) -> tuple[WorkerActivity, str | None]:
        with self._activity_lock:
            return self._desired_activity

    def _report_stop(self) -> None:
        if self._ensure_registered():
            self._report("stop", self._stop_worker)

    def _send_heartbeat(self) -> None:
        heartbeat_worker(instance_id=self._instance_id)

    def _register_worker(self) -> None:
        register_worker(
            instance_id=self._instance_id,
            worker_key=self._worker_key,
            display_name=self._display_name,
        )

    def _stop_worker(self) -> None:
        stop_worker(instance_id=self._instance_id)

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
