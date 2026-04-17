from __future__ import annotations

from pathlib import Path

from sqlmodel import Session

from card_reader_api.infrastructure import repositories
from card_reader_api.infrastructure.models import ImportJobStatus
from card_reader_api.infrastructure.parser import CardParser


class ImportService:
    def __init__(self, parser: CardParser) -> None:
        self._parser = parser

    def create_job(
        self,
        session: Session,
        *,
        source_path: str,
        template_id: str,
        options: dict[str, object],
    ):
        return repositories.create_import_job(
            session,
            source_path=Path(source_path),
            template_id=template_id,
            options=options,
        )

    def process_job(self, session: Session, job_id: str) -> None:
        job = repositories.fetch_job(session, job_id)
        if job is None:
            return
        repositories.mark_job_running(session, job)
        items = repositories.get_job_items(session, job.id)

        for item in items:
            if item.status != ImportJobStatus.queued:
                continue
            parsed = self._parser.parse(Path(item.source_file), job.template_id)
            repositories.save_parsed_card(
                session,
                item=item,
                template_id=job.template_id,
                checksum=parsed.checksum,
                normalized_fields=parsed.normalized_fields,
                confidence=parsed.confidence,
                raw_ocr=parsed.raw_ocr,
            )
            repositories.bump_job_processed(session, job)

        repositories.mark_job_complete(session, job)


class CardService:
    def list_cards(self, session: Session, *, query: str | None, max_confidence: float | None):
        return repositories.list_cards(session, query=query, max_confidence=max_confidence)

    def get_card_with_image(self, session: Session, card_id: str):
        card = repositories.get_card(session, card_id)
        if card is None:
            return None, None
        image = repositories.get_card_image(session, card_id)
        return card, image

    def update_card(
        self,
        session: Session,
        *,
        card_id: str,
        name: str | None,
        type_line: str | None,
        mana_cost: str | None,
        rules_text: str | None,
    ):
        return repositories.update_card(
            session,
            card_id=card_id,
            name=name,
            type_line=type_line,
            mana_cost=mana_cost,
            rules_text=rules_text,
        )


class ExportService:
    def export_cards_csv(self, session: Session, *, query: str | None) -> str:
        return repositories.export_cards_csv(session, query=query)
