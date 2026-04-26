from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from card_reader_api.seeds.users import seed_users_from_config


class Command(BaseCommand):
    help = "Create and update configured seed users from JSON."

    def handle(self, *args: Any, **options: Any) -> None:
        result = seed_users_from_config()
        if result is None:
            self.stdout.write("No seed users file configured.")
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed users processed. created={result.created} existing={result.existing}"
            )
        )
