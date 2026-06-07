from __future__ import annotations

from card_reader_core.models import PARSE_FLAG_ITEM_STATUSES, PARSE_FLAG_PROPERTY_KEYS


def is_parse_flag_property_key(value: object) -> bool:
    return isinstance(value, str) and value in PARSE_FLAG_PROPERTY_KEYS


def is_parse_flag_item_status(value: object) -> bool:
    return isinstance(value, str) and value in PARSE_FLAG_ITEM_STATUSES
