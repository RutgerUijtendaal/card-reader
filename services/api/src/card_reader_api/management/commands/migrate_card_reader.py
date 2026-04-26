from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Adopt an existing domain schema when needed, then run Django migrations."

    def handle(self, *args, **options) -> None:
        tables = set(connection.introspection.table_names())
        applied_core_migrations = self._applied_core_migrations()
        if "card" in tables and not applied_core_migrations:
            call_command("adopt_schema")
        call_command("migrate", interactive=False)

    def _applied_core_migrations(self) -> set[str]:
        if "django_migrations" not in connection.introspection.table_names():
            return set()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM django_migrations WHERE app = %s",
                ["card_reader_core"],
            )
            return {row[0] for row in cursor.fetchall()}
