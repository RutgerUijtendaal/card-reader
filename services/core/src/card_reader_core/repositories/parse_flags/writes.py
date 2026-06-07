from __future__ import annotations

from django.db import transaction

from card_reader_core.models import PARSE_FLAG_ITEM_OPEN, CardVersion, CardVersionParseFlag, CardVersionParseFlagItem, now_utc

from .queries import get_parse_flag
from .types import ParseFlagItemInput, ParseFlagItemStatus
from .validation import is_parse_flag_item_status, is_parse_flag_property_key


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
