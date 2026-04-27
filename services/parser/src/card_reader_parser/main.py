from __future__ import annotations

import faulthandler
import logging
import os
import signal
import time
from pathlib import Path
from threading import Event

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_core.django_settings")
import django

django.setup()

# Django-backed modules import models, so they must load after django.setup().
from card_reader_core.core_logging import configure_logging  # noqa: E402
from card_reader_core.database.connection import initialize_database  # noqa: E402
from card_reader_core.repositories.import_jobs_repository import (  # noqa: E402
    get_next_queued_job,
    requeue_running_import_jobs,
)
from card_reader_core.services.parser_jobs import ImportProcessorService  # noqa: E402
from card_reader_parser.parsers.card_parser import CardParser  # noqa: E402

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


def recover_interrupted_jobs() -> None:
    recovered_jobs, recovered_items = requeue_running_import_jobs()

    if recovered_jobs or recovered_items:
        logger.warning(
            "Recovered interrupted import work. jobs=%s items=%s",
            recovered_jobs,
            recovered_items,
        )


def run_parser_loop(interval_seconds: float = 1.5) -> None:
    # Emit Python stack traces if native extensions crash (SIGSEGV/SIGABRT).
    faulthandler.enable(all_threads=True)
    configure_logging()
    shutdown = ShutdownController()
    signal.signal(signal.SIGTERM, lambda signum, _frame: shutdown.request_stop(signum))
    signal.signal(signal.SIGINT, lambda signum, _frame: shutdown.request_stop(signum))

    parser = CardParser()
    service = ImportProcessorService(parser)
    initialize_database()
    recover_interrupted_jobs()
    logger.info("Parser loop started. interval_seconds=%.2f", interval_seconds)

    while not shutdown.should_stop():
        try:
            job = get_next_queued_job()
            if job is None:
                shutdown.interruptible_sleep(interval_seconds)
                continue
            logger.info(
                "Queued job claimed for processing. job_id=%s template_id=%s total_items=%s processed_items=%s",
                job.id,
                job.template_id,
                job.total_items,
                job.processed_items,
            )
            try:
                service.process_job(job.id, should_stop=shutdown.should_stop)
                logger.info("process_job returned. job_id=%s", job.id)
            except Exception:
                logger.exception("Unhandled parser error while processing job_id=%s", job.id)
        except Exception:
            logger.exception("Parser loop iteration failed; attempting recovery")
            try:
                initialize_database()
                recover_interrupted_jobs()
            except Exception:
                logger.exception("Parser recovery initialize_database failed")
            shutdown.interruptible_sleep(interval_seconds)
    logger.info("Parser loop stopped gracefully")


if __name__ == "__main__":
    run_parser_loop()




