from __future__ import annotations

from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from card_reader_api.seeds import run_registered_seeds


class Command(BaseCommand):
    help = "Seed default card reader catalog/template data."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--force", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        for result in run_registered_seeds(force=bool(options["force"])):
            self.stdout.write(
                f"{result.name}: skipped={result.skipped} "
                f"created={result.created} updated={result.updated}"
            )
