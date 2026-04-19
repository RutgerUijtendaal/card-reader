from __future__ import annotations

import logging
import os
import signal
import time
from threading import Event

from database.connection import get_session, initialize_database
from core_logging import configure_logging
from repositories import get_next_queued_job
from parsers.card_parser import CardParser
from services import ImportProcessorService
from template_store import DatabaseTemplateStore

logger = logging.getLogger(__name__)


class ShutdownController:
    def __init__(self) -> None:
        self._event = Event()
        marker = os.getenv("CARD_READER_SHUTDOWN_FILE")
        self._marker_file = Path(marker) if marker else None

    def request_stop(self, signum: int | None = None) -> None:
        if signum is not None:
            logger.info("Received shutdown signal signum=%s", signum)
        self._event.set()

    def should_stop(self) -> bool:
        if self._event.is_set():
            return True
        if self._marker_file is not None and self._marker_file.exists():
            logger.info("Shutdown marker detected. file=%s", self._marker_file)
            self._event.set()
            return True
        return False

    def interruptible_sleep(self, total_seconds: float, step_seconds: float = 0.2) -> None:
        elapsed = 0.0
        while elapsed < total_seconds and not self.should_stop():
            wait_for = min(step_seconds, total_seconds - elapsed)
            time.sleep(wait_for)
            elapsed += wait_for


def run_parser_loop(interval_seconds: float = 1.5) -> None:
    configure_logging()
    shutdown = ShutdownController()
    signal.signal(signal.SIGTERM, lambda signum, _frame: shutdown.request_stop(signum))
    signal.signal(signal.SIGINT, lambda signum, _frame: shutdown.request_stop(signum))

    template_store = DatabaseTemplateStore()
    parser = CardParser(template_store)
    service = ImportProcessorService(parser)
    initialize_database()

    while not shutdown.should_stop():
        try:
            with get_session() as session:
                job = get_next_queued_job(session)
                if job is None:
                    shutdown.interruptible_sleep(interval_seconds)
                    continue
                try:
                    service.process_job(session, job.id, should_stop=shutdown.should_stop)
                except Exception:
                    logger.exception("Unhandled parser error while processing job_id=%s", job.id)
        except Exception:
            logger.exception("Parser loop iteration failed; attempting recovery")
            try:
                initialize_database()
            except Exception:
                logger.exception("Parser recovery initialize_database failed")
            shutdown.interruptible_sleep(interval_seconds)
    logger.info("Parser loop stopped gracefully")


if __name__ == "__main__":
    run_parser_loop()
