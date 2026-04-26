from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from card_reader_core.db.schema_check import check_existing_schema


class Command(BaseCommand):
    help = "Verify an existing schema and fake-apply the initial Django migrations."

    def handle(self, *args, **options) -> None:
        result = check_existing_schema()
        if not result.ok:
            raise CommandError(
                "Cannot adopt schema. "
                f"missing_tables={result.missing_tables} "
                f"missing_columns={result.missing_columns}"
            )
        call_command(
            "migrate",
            "card_reader_core",
            "0005_card_version_search",
            fake=True,
            interactive=False,
        )
        self.stdout.write(self.style.SUCCESS("Existing card reader schema adopted."))
