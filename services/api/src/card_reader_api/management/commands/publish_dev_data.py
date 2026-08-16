from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError, CommandParser

from card_reader_core.config.settings import settings
from card_reader_core.operations.developer_data import (
    DeveloperDataError,
    DeveloperDataLock,
    PublishedBundleStore,
    validate_archive,
)
from card_reader_core.storage import calculate_checksum

from card_reader_api.developer_data.validation import validate_temporary_import


class Command(BaseCommand):
    help = "Publish an immutable, already-exported developer-data bundle."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("archive", help="Path to a validated developer-data .tar.gz archive.")
        parser.add_argument(
            "--api-base-url",
            default="https://maityscardgame.com/api",
            help="API URL written into the suggested lock-file payload.",
        )

    def handle(self, *args: object, **options: object) -> None:
        if settings.is_dev:
            raise CommandError("publish_dev_data is restricted to non-development environments.")
        archive_path = Path(str(options["archive"])).resolve()
        try:
            manifest, _payload = validate_archive(archive_path)
            archive_sha256 = calculate_checksum(archive_path)
            validate_temporary_import(
                archive_path=archive_path,
                bundle_version=manifest.bundle_version,
                archive_sha256=archive_sha256,
            )
            artifact = PublishedBundleStore().publish(archive_path)
        except (DeveloperDataError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        lock = DeveloperDataLock(
            bundle_version=artifact.bundle_version,
            format_version=artifact.format_version,
            sha256=artifact.sha256,
            api_base_url=str(options["api_base_url"]).rstrip("/"),
        )
        self.stdout.write(self.style.SUCCESS(f"Published {artifact.filename}"))
        self.stdout.write("Update dev-data.lock.json with:")
        self.stdout.write(json.dumps(lock.model_dump(mode="json"), indent=2, sort_keys=True))
