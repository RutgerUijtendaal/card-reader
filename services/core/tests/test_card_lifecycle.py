from __future__ import annotations

import os
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_core.django_settings")
django.setup()

from card_reader_core.models import (  # noqa: E402
    ACTIVE_CARD_LIFECYCLE_STATUS,
    ALL_CARD_LIFECYCLE_FILTER,
    DEFAULT_CARD_LIFECYCLE_FILTER,
    DEPRECATED_CARD_LIFECYCLE_STATUS,
    active_card_lifecycle_q,
    card_is_deprecated,
    card_is_visible_for_lifecycle,
    card_lifecycle_filter_q,
    normalize_card_lifecycle_filter,
)


def test_normalize_card_lifecycle_filter_defaults_unknown_values() -> None:
    assert normalize_card_lifecycle_filter(DEPRECATED_CARD_LIFECYCLE_STATUS) == DEPRECATED_CARD_LIFECYCLE_STATUS
    assert normalize_card_lifecycle_filter(ALL_CARD_LIFECYCLE_FILTER) == ALL_CARD_LIFECYCLE_FILTER
    assert normalize_card_lifecycle_filter("unknown") == DEFAULT_CARD_LIFECYCLE_FILTER


def test_card_lifecycle_visibility_predicates() -> None:
    active_card = SimpleNamespace(lifecycle_status=ACTIVE_CARD_LIFECYCLE_STATUS)
    deprecated_card = SimpleNamespace(lifecycle_status=DEPRECATED_CARD_LIFECYCLE_STATUS)

    assert not card_is_deprecated(active_card)
    assert card_is_deprecated(deprecated_card)
    assert card_is_visible_for_lifecycle(active_card, DEFAULT_CARD_LIFECYCLE_FILTER)
    assert not card_is_visible_for_lifecycle(deprecated_card, DEFAULT_CARD_LIFECYCLE_FILTER)
    assert card_is_visible_for_lifecycle(deprecated_card, ALL_CARD_LIFECYCLE_FILTER)


def test_card_lifecycle_filter_q_uses_empty_q_for_all() -> None:
    assert card_lifecycle_filter_q(ALL_CARD_LIFECYCLE_FILTER).children == []
    assert active_card_lifecycle_q(field_path="lifecycle_status").children == [
        ("lifecycle_status", ACTIVE_CARD_LIFECYCLE_STATUS),
    ]
