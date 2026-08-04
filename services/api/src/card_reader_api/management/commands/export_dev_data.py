from __future__ import annotations

from pathlib import Path
import subprocess

from django.core.management.base import BaseCommand, CommandError, CommandParser

from card_reader_core.operations.developer_data import DeveloperDataError, export_developer_data


class Command(BaseCommand):
    help = "Export a curated, sanitized developer-data archive without changing application data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--selection", required=True, help="Path to the reviewed selection JSON file.")
        parser.add_argument("--output", required=True, help="Destination .tar.gz path; it must not already exist.")

    def handle(self, *args: object, **options: object) -> None:
        try:
            manifest = export_developer_data(
                selection_path=Path(str(options["selection"])),
                output_path=Path(str(options["output"])),
                source_revision=_source_revision(),
            )
        except (DeveloperDataError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Exported developer-data bundle {manifest.bundle_version}: {manifest.counts}"
            )
        )


def _source_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"
