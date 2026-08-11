from __future__ import annotations

from django.db import transaction

from card_reader_core.models import DEFAULT_CARD_POOL, CardPool, CardRole, CardVersion, ImportJobItem
from card_reader_core.services.imports import CardRoleInferenceEvidence
from card_reader_core.repositories.cards import save_parsed_card_result
from card_reader_core.repositories.metadata import SuggestionCandidate
from card_reader_core.services.notifications import (
    DECK_CARD_VERSION_CHANGE_IMPORT_CREATED,
    NotificationService,
)
from card_reader_core.services.tts_card_sheets import TtsCardSheetService


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
    card_pool: CardPool = DEFAULT_CARD_POOL,
    resolved_card_roles: tuple[CardRole, ...] = (),
    classification_evidence: CardRoleInferenceEvidence | None = None,
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
        card_pool=card_pool,
        resolved_card_roles=resolved_card_roles,
        classification_evidence=classification_evidence,
    )
    version = result.version
    if result.created_new_version:
        card_id = version.card.id
        transaction.on_commit(
            lambda: NotificationService().notify_deck_owners_card_version_changed(
                card_id=version.card.id,
                card_version_id=version.id,
                previous_card_version_id=(
                    version.previous_version.id if version.previous_version is not None else None
                ),
                cause=DECK_CARD_VERSION_CHANGE_IMPORT_CREATED,
                import_job_id=item.job.id,
                import_item_id=item.id,
            ),
            robust=True,
        )
        transaction.on_commit(lambda: TtsCardSheetService().sync_cards([card_id]), robust=True)
    return version
