from __future__ import annotations

from django.db.models import Max, Prefetch, Q

from card_reader_core.models import PARSE_FLAG_ITEM_OPEN, CardVersionParseFlag, CardVersionParseFlagItem

from .types import PARSE_FLAG_OPEN_STATUS, PaginatedParseFlags, ParseFlagStatusFilter
from .validation import is_parse_flag_item_status


def get_parse_flag(flag_id: str) -> CardVersionParseFlag | None:
    return (
        CardVersionParseFlag.objects.select_related(
            "card_version",
            "card_version__card",
            "card_version__content_version",
            "submitted_by",
        )
        .prefetch_related("items")
        .filter(id=flag_id)
        .first()
    )


def count_open_parse_flag_items() -> int:
    return CardVersionParseFlagItem.objects.filter(status=PARSE_FLAG_ITEM_OPEN).count()


def list_parse_flags(
    *,
    status: ParseFlagStatusFilter = PARSE_FLAG_OPEN_STATUS,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedParseFlags:
    normalized_page = max(page, 1)
    normalized_page_size = max(1, min(page_size, 100))
    item_queryset = CardVersionParseFlagItem.objects.select_related("reviewed_by").order_by("created_at", "id")
    latest_item_filter = Q()
    if status != "all":
        if not is_parse_flag_item_status(status):
            raise ValueError("Invalid parse flag status.")
        item_queryset = item_queryset.filter(status=status)
        latest_item_filter = Q(items__status=status)
    latest_item_created_at = (
        Max("items__created_at") if status == "all" else Max("items__created_at", filter=latest_item_filter)
    )

    queryset = (
        CardVersionParseFlag.objects.select_related(
            "submitted_by",
            "card_version",
            "card_version__card",
            "card_version__content_version",
        )
        .prefetch_related(
            Prefetch("items", queryset=item_queryset),
            Prefetch("card_version__images"),
        )
        .annotate(latest_item_created_at=latest_item_created_at)
        .order_by("-latest_item_created_at", "-created_at", "id")
    )
    if status != "all":
        queryset = queryset.filter(items__status=status).distinct()

    total_count = queryset.count()
    offset = (normalized_page - 1) * normalized_page_size
    return PaginatedParseFlags(
        count=total_count,
        page=normalized_page,
        page_size=normalized_page_size,
        results=list(queryset[offset : offset + normalized_page_size]),
    )
