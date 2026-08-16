from __future__ import annotations

from django.db import transaction

from card_reader_core.models import (
    CLASSIFICATION_REVIEW_OPEN,
    CLASSIFICATION_REVIEW_STATUSES,
    Card,
    CardClassificationReviewItem,
    CardPoolScope,
    CardVersion,
    ImportJobItem,
    now_utc,
)

from .types import ClassificationReviewStatus
from .queries import classification_review_card_pool_scope_q


def create_classification_review_item(
    *,
    import_item: ImportJobItem,
    card: Card,
    card_version: CardVersion,
    existing_classification: dict[str, object],
    inferred_classification: dict[str, object],
    inference_evidence: dict[str, object],
) -> CardClassificationReviewItem:
    item, _created = CardClassificationReviewItem.objects.get_or_create(
        import_item=import_item,
        defaults={
            "card": card,
            "card_version": card_version,
            "card_pool": card.card_pool,
            "existing_classification_json": existing_classification,
            "inferred_classification_json": inferred_classification,
            "inference_evidence_json": inference_evidence,
        },
    )
    return item


def update_classification_review_item_status(
    *,
    item_id: str,
    status: ClassificationReviewStatus,
    reviewed_by_id: str,
    card_pool_scope: CardPoolScope,
    review_note: str = "",
) -> CardClassificationReviewItem | None:
    if status == CLASSIFICATION_REVIEW_OPEN or status not in CLASSIFICATION_REVIEW_STATUSES:
        raise ValueError("Classification review can only be resolved or dismissed.")
    with transaction.atomic():
        item = (
            CardClassificationReviewItem.objects.select_for_update()
            .select_related(
                "import_item",
                "import_item__job",
                "card",
                "card_version",
                "card_version__content_version",
                "reviewed_by",
            )
            .filter(id=item_id)
            .filter(classification_review_card_pool_scope_q(card_pool_scope))
            .first()
        )
        if item is None:
            return None
        if item.status == status:
            return item
        if item.status != CLASSIFICATION_REVIEW_OPEN:
            raise ValueError("Classification review has already been completed.")
        item.status = status
        setattr(item, "reviewed_by_id", reviewed_by_id)
        item.review_note = review_note.strip()
        item.reviewed_at = now_utc()
        item.updated_at = now_utc()
        item.save(
            update_fields=[
                "status",
                "reviewed_by",
                "review_note",
                "reviewed_at",
                "updated_at",
            ]
        )
    return item


def retarget_classification_review_items(
    *,
    source_card_ids: list[str],
    target_card: Card,
) -> None:
    CardClassificationReviewItem.objects.filter(card_id__in=source_card_ids).update(
        card=target_card,
        updated_at=now_utc(),
    )
