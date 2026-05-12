from __future__ import annotations

from dataclasses import dataclass

from card_reader_core.repositories.cards_repository import (
    get_card,
    get_card_image,
    get_latest_card_version,
    resolve_image_file_path,
)
from card_reader_core.repositories.import_jobs_repository import create_import_job_with_files
from card_reader_core.settings import settings


class CardReparseError(ValueError):
    pass


@dataclass(slots=True)
class CardReparseQueueResult:
    job_id: str
    message: str


class CardActionService:
    def queue_latest_version_reparse(self, card_id: str) -> CardReparseQueueResult | None:
        card = get_card(card_id)
        version = get_latest_card_version(card_id)
        if card is None or version is None:
            return None

        image = get_card_image(version.id)
        if image is None:
            raise CardReparseError("Latest card image is not available for reparse.")

        image_path = resolve_image_file_path(image)
        if image_path is None:
            raise CardReparseError("Latest card image file is missing for reparse.")

        job = create_import_job_with_files(
            source_path=settings.storage_root_dir / "cards" / card.id / "reparse-latest",
            template_id=version.template.key,
            options={"reparse_existing": True},
            files=[image_path],
        )
        return CardReparseQueueResult(
            job_id=job.id,
            message="Queued reparse job for the latest card image.",
        )
