from __future__ import annotations

from card_reader_core.models import (
    CARD_FACTION_DEFINITIONS,
    CARD_POOL_DEFINITIONS,
    CARD_ROLE_DEFINITIONS,
    CARD_ROLE_FILTER_DEFINITIONS,
    CARD_ROLES,
    STANDARD_CARD_ROLE,
    card_faction_identity_key,
    normalize_card_factions,
    normalize_card_roles,
)


def test_classification_registries_expose_the_final_canonical_contract() -> None:
    assert [
        (definition.key, definition.label, definition.rank)
        for definition in CARD_POOL_DEFINITIONS
    ] == [
        ("player", "Player", 0),
        ("evil", "Evil", 1),
        ("neutral", "Neutral", 2),
    ]
    assert [
        (definition.key, definition.label, definition.rank)
        for definition in CARD_ROLE_DEFINITIONS
    ] == [
        ("hero", "Hero", 1),
        ("boss", "Boss", 2),
        ("location", "Location", 3),
        ("boon", "Boon", 4),
        ("event", "Event", 5),
        ("shop_item", "Shop Item", 6),
        ("mana", "Mana", 7),
    ]
    assert [
        (definition.key, definition.label, definition.rank)
        for definition in CARD_FACTION_DEFINITIONS
    ] == [
        ("order", "Order", 1),
        ("blood", "Blood", 2),
        ("dark", "Dark", 3),
        ("metal", "Metal", 4),
    ]


def test_normal_is_only_the_derived_empty_role_filter() -> None:
    assert STANDARD_CARD_ROLE not in CARD_ROLES
    assert [
        (definition.key, definition.label, definition.rank, definition.derived)
        for definition in CARD_ROLE_FILTER_DEFINITIONS
    ] == [
        ("standard", "Normal", 0, True),
        ("hero", "Hero", 1, False),
        ("boss", "Boss", 2, False),
        ("location", "Location", 3, False),
        ("boon", "Boon", 4, False),
        ("event", "Event", 5, False),
        ("shop_item", "Shop Item", 6, False),
        ("mana", "Mana", 7, False),
    ]


def test_role_and_faction_normalization_are_independent_and_canonical() -> None:
    assert normalize_card_roles(("mana", "event", "hero", "event", "unknown")) == (
        "hero",
        "event",
        "mana",
    )
    assert normalize_card_factions(("metal", "dark", "order", "dark", "unsupported")) == (
        "order",
        "dark",
        "metal",
    )
    assert card_faction_identity_key(("metal", "dark", "order", "dark")) == (
        '["order","dark","metal"]'
    )
