from __future__ import annotations

import logging
import time
from pathlib import Path

from database.connection import get_session, initialize_database
from core_logging import configure_logging
from repositories import get_next_queued_job
from parsers.card_parser import CardParser
from services import ImportProcessorService
from template_store import FileTemplateStore

logger = logging.getLogger(__name__)


def run_parser_loop(interval_seconds: float = 1.5) -> None:
    configure_logging()
    template_store = FileTemplateStore(Path(__file__).resolve().parent / "parsers" / "templates")
    parser = CardParser(template_store)
    service = ImportProcessorService(parser)
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
                logger.exception("Unhandled parser error while processing job_id=%s", job.id)


if __name__ == "__main__":
    run_parser_loop()
