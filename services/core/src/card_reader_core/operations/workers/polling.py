from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from pathlib import Path
import signal
from threading import Event
import time
from typing import Generic, TypeVar

from .heartbeat import DEFAULT_WORKER_HEARTBEAT_INTERVAL_SECONDS, WorkerHeartbeatSession

WorkItem = TypeVar("WorkItem")
StopRequested = Callable[[], bool]


@dataclass(frozen=True)
class PollingWorkerConfig:
    name: str
    interval_seconds: float
    key: str | None = None
    heartbeat_interval_seconds: float = DEFAULT_WORKER_HEARTBEAT_INTERVAL_SECONDS
    once: bool = False
    shutdown_marker: Path | None = None


class WorkerShutdownController:
    def __init__(
        self,
        *,
        worker_name: str,
        logger: logging.Logger,
        marker_file: Path | None = None,
    ) -> None:
        self._worker_name = worker_name
        self._logger = logger
        self._marker_file = marker_file
        self._event = Event()

    def install_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, lambda signum, _frame: self.request_stop(signum))
        signal.signal(signal.SIGINT, lambda signum, _frame: self.request_stop(signum))

    def request_stop(self, signum: int | None = None) -> None:
        if signum is not None:
            self._logger.info(
                "%s received shutdown signal. signum=%s",
                self._worker_name,
                signum,
            )
        self._event.set()

    def should_stop(self) -> bool:
        if self._event.is_set():
            return True
        if self._marker_file is not None and self._marker_file.exists():
            self._logger.info(
                "%s shutdown marker detected. file=%s",
                self._worker_name,
                self._marker_file,
            )
            self._event.set()
            return True
        return False

    def interruptible_wait(self, total_seconds: float) -> None:
        deadline = time.monotonic() + max(0.0, total_seconds)
        while not self.should_stop():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            self._event.wait(min(0.2, remaining))


class PollingWorker(Generic[WorkItem]):
    def __init__(
        self,
        *,
        config: PollingWorkerConfig,
        logger: logging.Logger,
        claim_next: Callable[[], WorkItem | None],
        process: Callable[[WorkItem, StopRequested], None],
        initialize: Callable[[], None] | None = None,
        recover: Callable[[], None] | None = None,
        on_claimed: Callable[[WorkItem], None] | None = None,
        on_processed: Callable[[WorkItem], None] | None = None,
        work_identifier: Callable[[WorkItem], str] = str,
    ) -> None:
        self._config = config
        self._logger = logger
        self._claim_next = claim_next
        self._process = process
        self._initialize = initialize or _noop
        self._recover = recover or _noop
        self._on_claimed = on_claimed or _noop_work
        self._on_processed = on_processed or _noop_work
        self._work_identifier = work_identifier
        self._shutdown = WorkerShutdownController(
            worker_name=config.name,
            logger=logger,
            marker_file=config.shutdown_marker,
        )
        self._heartbeat: WorkerHeartbeatSession | None = None
        if config.key is not None:
            self._heartbeat = WorkerHeartbeatSession(
                worker_key=config.key,
                display_name=config.name,
                logger=logger,
                interval_seconds=config.heartbeat_interval_seconds,
            )

    def run(self) -> None:
        self._shutdown.install_signal_handlers()
        if not self._initialize_and_recover_for_startup():
            self._logger.info("%s stopped before startup completed", self._config.name)
            return
        if self._heartbeat is not None:
            self._heartbeat.start()
        try:
            self._logger.info(
                "%s loop started. interval_seconds=%.2f",
                self._config.name,
                self._config.interval_seconds,
            )
            while not self._shutdown.should_stop():
                self._run_iteration()
                if self._config.once:
                    break
            self._logger.info("%s loop stopped gracefully", self._config.name)
        finally:
            if self._heartbeat is not None:
                self._heartbeat.stop()

    def _initialize_and_recover_for_startup(self) -> bool:
        while not self._shutdown.should_stop():
            try:
                self._initialize_and_recover()
                return True
            except Exception:
                if self._config.once:
                    raise
                self._logger.exception(
                    "%s startup failed; retrying",
                    self._config.name,
                )
                self._shutdown.interruptible_wait(self._config.interval_seconds)
        return False

    def _run_iteration(self) -> None:
        try:
            work = self._claim_next()
            if work is None:
                if self._heartbeat is not None:
                    self._heartbeat.mark_idle()
                if not self._config.once:
                    self._shutdown.interruptible_wait(self._config.interval_seconds)
                return
            if self._heartbeat is not None:
                self._heartbeat.mark_busy(self._work_identifier(work))
            self._on_claimed(work)
            try:
                self._process(work, self._shutdown.should_stop)
                self._on_processed(work)
            except Exception:
                self._logger.exception(
                    "Unhandled %s error while processing work_id=%s",
                    self._config.name,
                    self._work_identifier(work),
                )
            finally:
                if self._heartbeat is not None:
                    self._heartbeat.mark_idle()
            return
        except Exception:
            self._logger.exception(
                "%s loop iteration failed; attempting recovery",
                self._config.name,
            )
            self._initialize_and_recover(log_failure=True)
            if not self._config.once:
                self._shutdown.interruptible_wait(self._config.interval_seconds)

    def _initialize_and_recover(self, *, log_failure: bool = False) -> None:
        try:
            self._initialize()
            self._recover()
        except Exception:
            if not log_failure:
                raise
            self._logger.exception("%s recovery failed", self._config.name)


def _noop() -> None:
    return None


def _noop_work(_work: object) -> None:
    return None
