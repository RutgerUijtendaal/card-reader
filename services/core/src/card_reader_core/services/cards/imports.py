from __future__ import annotations

from django.db import transaction

from card_reader_core.models import CardVersion, ImportJobItem
from card_reader_core.repositories.cards import save_parsed_card_result
from card_reader_core.repositories.metadata import SuggestionCandidate
from card_reader_core.services.notifications import NotificationService


def save_parsed_card_with_notifications(
    *,
    item: ImportJobItem,
    template_id: str,
    checksum: str,
    normalized_fields: dict[str, str],
    confidence: dict[str, float],
    raw_ocr: dict[str, object],
    keyword_ids: list[str] | None = None,
    tag_ids: list[str] | None = None,
    type_ids: list[str] | None = None,
    symbol_ids: list[str] | None = None,
    tag_suggestions: list[SuggestionCandidate] | None = None,
    type_suggestions: list[SuggestionCandidate] | None = None,
    reparse_existing: bool = True,
) -> CardVersion:
    result = save_parsed_card_result(
        item=item,
        template_id=template_id,
        checksum=checksum,
        normalized_fields=normalized_fields,
        confidence=confidence,
        raw_ocr=raw_ocr,
        keyword_ids=keyword_ids,
        tag_ids=tag_ids,
        type_ids=type_ids,
        symbol_ids=symbol_ids,
        tag_suggestions=tag_suggestions,
        type_suggestions=type_suggestions,
        reparse_existing=reparse_existing,
    )
    version = result.version
    if result.created_new_version:
        transaction.on_commit(
            lambda: NotificationService().notify_deck_owners_card_changed(
                card_id=version.card.id,
                change_label="replaced by an import",
                metadata={
                    "source": "import",
                    "import_job_id": item.job.id,
                    "import_item_id": item.id,
                    "card_version_id": version.id,
                },
            )
        )
    return version
