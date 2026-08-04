from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandParser

from card_reader_api.developer_data.build_worker import process_developer_data_build
from card_reader_core.models import DeveloperDataBuild
from card_reader_core.operations.workers import PollingWorker, PollingWorkerConfig, StopRequested
from card_reader_core.repositories.developer_data import claim_next_build, requeue_interrupted_builds

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process queued developer-data builds outside the API request process."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--once", action="store_true", help="Process at most one queued build.")
        parser.add_argument("--poll-seconds", type=float, default=2.0)

    def handle(self, *args: object, **options: object) -> None:
        once = bool(options["once"])
        poll_seconds = max(0.2, float(str(options["poll_seconds"])))

        def process_build(build: DeveloperDataBuild, _should_stop: StopRequested) -> None:
            process_developer_data_build(build)

        def recover_builds() -> None:
            recovered = requeue_interrupted_builds()
            if recovered:
                logger.warning("Requeued interrupted developer-data builds. count=%s", recovered)

        PollingWorker[DeveloperDataBuild](
            config=PollingWorkerConfig(
                name="Developer-data builder",
                interval_seconds=poll_seconds,
                once=once,
            ),
            logger=logger,
            claim_next=claim_next_build,
            process=process_build,
            recover=recover_builds,
            work_identifier=lambda build: build.id,
        ).run()
