from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from card_reader_core.services.cards import convert_card_images_to_webp, format_byte_count


class Command(BaseCommand):
    help = "Convert canonical card image files to WebP and update CardVersionImage paths."

    def handle(self, *args: object, **options: object) -> None:
        result = convert_card_images_to_webp()
        self.stdout.write(result.message)
        self.stdout.write(
            "Before: "
            f"{format_byte_count(result.bytes_before)}; "
            f"after: {format_byte_count(result.bytes_after)}"
        )
        for failure in result.failures:
            self.stderr.write(f"{failure.image_id} {failure.path}: {failure.detail}")
        if result.failed:
            raise CommandError(f"{result.failed} card image conversion failed.")
