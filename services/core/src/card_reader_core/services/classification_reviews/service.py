from __future__ import annotations

from card_reader_core.models import CardClassificationReviewItem, CardPoolScope
from card_reader_core.repositories.classification_reviews import (
    ClassificationReviewStatus,
    update_classification_review_item_status,
)


def review_classification_item(
    *,
    item_id: str,
    status: ClassificationReviewStatus,
    reviewed_by_id: str,
    card_pool_scope: CardPoolScope,
    review_note: str = "",
) -> CardClassificationReviewItem | None:
    return update_classification_review_item_status(
        item_id=item_id,
        status=status,
        reviewed_by_id=reviewed_by_id,
        card_pool_scope=card_pool_scope,
        review_note=review_note,
    )
