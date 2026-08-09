from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from card_reader_api.seeds.notification_examples import seed_notification_examples
from card_reader_core.config import settings


class Command(BaseCommand):
    help = "Create idempotent development-only notification inbox examples."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--username",
            help="Seed only this active staff user; defaults to every active staff user.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.is_dev:
            raise CommandError("Notification examples are disabled outside development environments.")

        username = str(options.get("username") or "").strip() or None
        result = seed_notification_examples(username=username)
        self.stdout.write(
            self.style.SUCCESS(
                "Notification examples processed. "
                f"recipients={result.recipients} "
                f"created_notifications={result.created_notifications} "
                f"existing_notifications={result.existing_notifications} "
                f"created_decks={result.created_decks} "
                f"updated_decks={result.updated_decks} "
                f"skipped_recipients={result.skipped_recipients}"
            )
        )
