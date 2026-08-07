from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandParser

from card_reader_core.models import TtsCardSheet
from card_reader_core.operations.workers import PollingWorker, PollingWorkerConfig, StopRequested
from card_reader_core.repositories.tts_card_sheets import claim_next_renderable_sheet
from card_reader_core.services.tts_card_sheets import TtsCardSheetService, render_claimed_sheet

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the background TTS card-sheet renderer."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--interval", type=float, default=1.0)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        interval = max(0.1, float(str(options["interval"])))

        def process(sheet: TtsCardSheet, should_stop: StopRequested) -> None:
            if should_stop():
                return
            render_claimed_sheet(sheet)

        def recover() -> None:
            TtsCardSheetService().reconcile_all(render=False)

        PollingWorker[TtsCardSheet](
            config=PollingWorkerConfig(
                name="TTS card-sheet renderer",
                interval_seconds=interval,
                once=bool(options["once"]),
            ),
            logger=logger,
            claim_next=claim_next_renderable_sheet,
            process=process,
            recover=recover,
            work_identifier=lambda sheet: str(sheet.id),
        ).run()
