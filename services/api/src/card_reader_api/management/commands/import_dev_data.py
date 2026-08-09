from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError, CommandParser

from card_reader_core.operations.developer_data import DeveloperDataError, import_developer_data
from card_reader_core.services.tts_card_sheets import TtsCardSheetService


class Command(BaseCommand):
    help = "Import a validated developer-data archive into an empty domain database."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("archive", help="Path to the developer-data .tar.gz archive.")
        parser.add_argument("--bundle-version")
        parser.add_argument("--sha256")

    def handle(self, *args: object, **options: object) -> None:
        try:
            result = import_developer_data(
                archive_path=Path(str(options["archive"])),
                expected_bundle_version=_optional_string(options.get("bundle_version")),
                expected_archive_sha256=_optional_string(options.get("sha256")),
            )
        except (DeveloperDataError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        sheet_result = TtsCardSheetService().reconcile_all(
            render=True,
            progress=self.stdout.write,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported developer-data bundle {result.bundle_version}; "
                f"copied {result.copied_assets} assets."
                f" Generated {sheet_result.affected_sheets} TTS card sheets."
            )
        )


def _optional_string(value: object) -> str | None:
    compact = str(value or "").strip()
    return compact or None
