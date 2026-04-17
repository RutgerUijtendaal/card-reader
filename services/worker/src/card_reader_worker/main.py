from __future__ import annotations

import logging
import time
from pathlib import Path

from card_reader_api.application.services import ImportService
from card_reader_api.infrastructure.db import get_session, initialize_database
from card_reader_api.infrastructure.logging_utils import configure_logging
from card_reader_api.infrastructure.parser import CardParser
from card_reader_api.infrastructure.repositories import get_next_queued_job

logger = logging.getLogger(__name__)


def run_worker_loop(interval_seconds: float = 1.5) -> None:
    configure_logging()
    parser = CardParser(Path(__file__).resolve().parents[3] / "api" / "src" / "card_reader_api" / "infrastructure" / "templates")
    service = ImportService(parser)
    initialize_database()

    while True:
        with get_session() as session:
            job = get_next_queued_job(session)
            if job is None:
                time.sleep(interval_seconds)
                continue
            try:
                service.process_job(session, job.id)
            except Exception:
                logger.exception("Unhandled worker error while processing job_id=%s", job.id)


if __name__ == "__main__":
    run_worker_loop()
