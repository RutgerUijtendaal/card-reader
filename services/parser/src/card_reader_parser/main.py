from __future__ import annotations

import faulthandler
import logging
import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_core.django_settings")
import django

django.setup()

# Django-backed modules import models, so they must load after django.setup().
from card_reader_core.config.logging import configure_logging  # noqa: E402
from card_reader_core.database.connection import initialize_database  # noqa: E402
from card_reader_core.models import ImportJob  # noqa: E402
from card_reader_core.operations.workers import (  # noqa: E402
    PollingWorker,
    PollingWorkerConfig,
    StopRequested,
)
from card_reader_core.repositories.import_jobs import (  # noqa: E402
    get_next_queued_job,
    requeue_running_import_jobs,
)
from card_reader_core.services.parser_jobs import ImportProcessorService  # noqa: E402
from card_reader_parser.parsers.card_parser import CardParser  # noqa: E402

logger = logging.getLogger(__name__)


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
    parser = CardParser()
    service = ImportProcessorService(parser)
    marker = os.getenv("CARD_READER_SHUTDOWN_FILE")

    def process_job(job: ImportJob, should_stop: StopRequested) -> None:
        service.process_job(job.id, should_stop=should_stop)

    def log_claimed_job(job: ImportJob) -> None:
        logger.info(
            "Queued job claimed for processing. job_id=%s template_id=%s total_items=%s processed_items=%s",
            job.id,
            job.template.key,
            job.total_items,
            job.processed_items,
        )

    def log_processed_job(job: ImportJob) -> None:
        logger.info("process_job returned. job_id=%s", job.id)

    PollingWorker[ImportJob](
        config=PollingWorkerConfig(
            name="Parser worker",
            interval_seconds=interval_seconds,
            shutdown_marker=Path(marker) if marker else None,
        ),
        logger=logger,
        claim_next=get_next_queued_job,
        process=process_job,
        initialize=initialize_database,
        recover=recover_interrupted_jobs,
        on_claimed=log_claimed_job,
        on_processed=log_processed_job,
        work_identifier=lambda job: job.id,
    ).run()


if __name__ == "__main__":
    run_parser_loop()


