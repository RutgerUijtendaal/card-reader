from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from django.db import transaction
from django.db.models import Max, Prefetch, Q

from card_reader_core.models import (
    PARSE_FLAG_ITEM_OPEN,
    PARSE_FLAG_ITEM_STATUSES,
    PARSE_FLAG_PROPERTY_KEYS,
    CardVersion,
    CardVersionParseFlag,
    CardVersionParseFlagItem,
    now_utc,
)

ParseFlagItemStatus = Literal["open", "resolved", "dismissed"]
ParseFlagStatusFilter = ParseFlagItemStatus | Literal["all"]
PARSE_FLAG_OPEN_STATUS: ParseFlagItemStatus = "open"


@dataclass(frozen=True)
class ParseFlagItemInput:
    property_key: str
    expected_value: str = ""
    note: str = ""


@dataclass(frozen=True)
class PaginatedParseFlags:
    count: int
    page: int
    page_size: int
    results: list[CardVersionParseFlag]


def is_parse_flag_property_key(value: object) -> bool:
    return isinstance(value, str) and value in PARSE_FLAG_PROPERTY_KEYS


def is_parse_flag_item_status(value: object) -> bool:
    return isinstance(value, str) and value in PARSE_FLAG_ITEM_STATUSES


def create_card_version_parse_flag(
    *,
    card_id: str,
    version_id: str,
    submitted_by_id: str,
    note: str,
    items: list[ParseFlagItemInput],
    captured_values: dict[str, str],
) -> CardVersionParseFlag | None:
    version = CardVersion.objects.select_related("card").filter(id=version_id, card_id=card_id).first()
    if version is None:
        return None
    if not items:
        raise ValueError("At least one flagged property is required.")
    invalid_keys = [item.property_key for item in items if not is_parse_flag_property_key(item.property_key)]
    if invalid_keys:
        raise ValueError("Invalid flagged property.")

    with transaction.atomic():
        flag = CardVersionParseFlag.objects.create(
            card_version=version,
            submitted_by_id=submitted_by_id,
            note=note.strip(),
        )
        CardVersionParseFlagItem.objects.bulk_create(
            [
                CardVersionParseFlagItem(
                    flag=flag,
                    property_key=item.property_key,
                    captured_current_value=captured_values.get(item.property_key, ""),
                    expected_value=item.expected_value.strip(),
                    note=item.note.strip(),
                )
                for item in items
            ]
        )
    return get_parse_flag(flag.id)


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
        .annotate(
            latest_item_created_at=latest_item_created_at
        )
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


def update_parse_flag_item_status(
    *,
    item_id: str,
    status: ParseFlagItemStatus,
    reviewed_by_id: str,
    review_note: str = "",
) -> CardVersionParseFlagItem | None:
    if status == PARSE_FLAG_ITEM_OPEN or not is_parse_flag_item_status(status):
        raise ValueError("Flag item can only be resolved or dismissed.")
    item = (
        CardVersionParseFlagItem.objects.select_related(
            "flag",
            "flag__submitted_by",
            "flag__card_version",
            "flag__card_version__card",
            "flag__card_version__content_version",
            "reviewed_by",
        )
        .filter(id=item_id)
        .first()
    )
    if item is None:
        return None
    item.status = status
    setattr(item, "reviewed_by_id", reviewed_by_id)
    item.review_note = review_note.strip()
    item.reviewed_at = now_utc()
    item.updated_at = now_utc()
    item.save(update_fields=["status", "reviewed_by", "review_note", "reviewed_at", "updated_at"])
    return item


__all__ = [
    "PaginatedParseFlags",
    "ParseFlagItemInput",
    "ParseFlagItemStatus",
    "ParseFlagStatusFilter",
    "count_open_parse_flag_items",
    "create_card_version_parse_flag",
    "get_parse_flag",
    "is_parse_flag_item_status",
    "is_parse_flag_property_key",
    "list_parse_flags",
    "update_parse_flag_item_status",
]
