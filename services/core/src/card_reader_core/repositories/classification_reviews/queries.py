from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from card_reader_core.models import (
    CLASSIFICATION_REVIEW_OPEN,
    CardClassificationReviewItem,
    CardVersionImage,
)

from .types import (
    CLASSIFICATION_REVIEW_OPEN_STATUS,
    ClassificationReviewStatusFilter,
    PaginatedClassificationReviewItems,
)


def _review_items() -> QuerySet[CardClassificationReviewItem]:
    return CardClassificationReviewItem.objects.select_related(
        "import_item",
        "import_item__job",
        "card",
        "card_version",
        "card_version__content_version",
        "reviewed_by",
    ).prefetch_related(
        "card__role_assignments",
        "card__faction_assignments",
        "card__mana_family_assignments",
        Prefetch(
            "card_version__images",
            queryset=CardVersionImage.objects.order_by("-created_at"),
        ),
    )


def count_open_classification_review_items() -> int:
    return CardClassificationReviewItem.objects.filter(status=CLASSIFICATION_REVIEW_OPEN).count()


def list_classification_review_items(
    *,
    status: ClassificationReviewStatusFilter = CLASSIFICATION_REVIEW_OPEN_STATUS,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedClassificationReviewItems:
    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    queryset = _review_items()
    if status != "all":
        queryset = queryset.filter(status=status)
    queryset = queryset.order_by("-created_at", "id")
    total_count = queryset.count()
    offset = (normalized_page - 1) * normalized_page_size
    return PaginatedClassificationReviewItems(
        count=total_count,
        page=normalized_page,
        page_size=normalized_page_size,
        results=list(queryset[offset : offset + normalized_page_size]),
    )
