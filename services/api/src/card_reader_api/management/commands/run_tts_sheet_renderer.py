from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandParser

from card_reader_core.models import TtsCardSheet
from card_reader_core.operations.workers import PollingWorker, PollingWorkerConfig, StopRequested
from card_reader_core.repositories.tts_card_sheets import (
    claim_next_renderable_sheet,
    release_render_claim,
)
from card_reader_core.services.tts_card_sheets import TtsCardSheetService, render_claimed_sheet

logger = logging.getLogger(__name__)


def _process_claimed_sheet(sheet: TtsCardSheet, should_stop: StopRequested) -> None:
    if should_stop():
        release_render_claim(
            sheet_id=str(sheet.id),
            claimed_at=sheet.render_claimed_at,
        )
        return
    render_claimed_sheet(sheet)


def _recover_renderer() -> None:
    TtsCardSheetService().recover_renderer()


class Command(BaseCommand):
    help = "Run the background TTS card-sheet renderer."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--interval", type=float, default=1.0)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        interval = max(0.1, float(str(options["interval"])))

        PollingWorker[TtsCardSheet](
            config=PollingWorkerConfig(
                key="tts-sheet-renderer",
                name="TTS card-sheet renderer",
                interval_seconds=interval,
                once=bool(options["once"]),
            ),
            logger=logger,
            claim_next=claim_next_renderable_sheet,
            process=_process_claimed_sheet,
            recover=_recover_renderer,
            work_identifier=lambda sheet: str(sheet.id),
        ).run()
