from __future__ import annotations

import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[3] / "api" / "src"))

from card_reader_api.application.services import ImportService
from card_reader_api.infrastructure.db import get_session, initialize_database
from card_reader_api.infrastructure.parser import CardParser
from card_reader_api.infrastructure.repositories import get_next_queued_job


def run_worker_loop(interval_seconds: float = 1.5) -> None:
    parser = CardParser(Path(__file__).resolve().parents[3] / "api" / "src" / "card_reader_api" / "infrastructure" / "templates")
    service = ImportService(parser)
    initialize_database()

    while True:
        with get_session() as session:
            job = get_next_queued_job(session)
            if job is None:
                time.sleep(interval_seconds)
                continue
            service.process_job(session, job.id)


if __name__ == "__main__":
    run_worker_loop()
