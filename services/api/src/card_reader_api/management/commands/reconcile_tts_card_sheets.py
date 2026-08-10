from __future__ import annotations

from django.core.management.base import BaseCommand, CommandParser

from card_reader_core.services.tts_card_sheets import TtsCardSheetService


class Command(BaseCommand):
    help = "Assign Cards to persistent TTS sheets and optionally render affected sheets."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--render", action="store_true")
        parser.add_argument("--force", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        result = TtsCardSheetService().reconcile_all(
            render=bool(options["render"]),
            force=bool(options["force"]),
            progress=self.stdout.write,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Reconciled TTS sheets: "
                f"usable_cards={result.usable_cards} "
                f"assigned_cards={result.assigned_cards} "
                f"affected_sheets={result.affected_sheets} "
                f"rendered_sheets={result.rendered_sheets}."
            )
        )
