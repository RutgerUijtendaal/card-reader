from card_reader_core.metadata import (
    MANA_FAMILIES,
    NO_MANA_FAMILY_SORT_KEY,
    mana_family_keys_for_symbol_keys,
    mana_family_sort_key,
    mana_family_sort_key_for_family_keys,
    normalize_mana_family_keys,
)


def test_mana_family_catalog_has_the_release_owned_order() -> None:
    assert [(family.key, family.label, family.rank) for family in MANA_FAMILIES] == [
        ("arcane", "Arcane", 0),
        ("dark", "Dark", 1),
        ("divine", "Divine", 2),
        ("martial", "Martial", 3),
        ("occult", "Occult", 4),
        ("primal", "Primal", 5),
    ]
    assert [family.display_symbol_key for family in MANA_FAMILIES] == [
        "arcane-mana",
        "dark-mana",
        "divine-mana",
        "martial-mana",
        "occult-mana",
        "primal-mana",
    ]


def test_stored_family_normalization_is_canonical_and_empty_is_colorless() -> None:
    assert normalize_mana_family_keys(("primal", "arcane", "primal", "unknown")) == (
        "arcane",
        "primal",
    )
    assert mana_family_sort_key_for_family_keys(()) == NO_MANA_FAMILY_SORT_KEY
    assert mana_family_sort_key_for_family_keys(("arcane", "dark")) == 1


def test_mana_and_affinity_aliases_resolve_to_one_family() -> None:
    assert mana_family_keys_for_symbol_keys(
        ["arcane-mana", "arcane-affinity", "dark-affinity"]
    ) == ("arcane", "dark")
    assert mana_family_sort_key(["arcane-mana", "arcane-affinity"]) == 0


def test_legacy_primal_affinity_alias_is_accepted_without_becoming_canonical() -> None:
    primal = MANA_FAMILIES[-1]

    assert mana_family_keys_for_symbol_keys(["primla-affinity"]) == ("primal",)
    assert mana_family_sort_key(["primla-affinity"]) == mana_family_sort_key_for_family_keys(
        (primal.key,)
    )
    assert primal.affinity_symbol_key == "primal-affinity"


def test_sort_keys_use_earliest_family_then_complete_membership_and_no_family_last() -> None:
    arcane = mana_family_sort_key(["arcane-mana"])
    arcane_dark = mana_family_sort_key(["arcane-mana", "dark-affinity"])
    arcane_divine = mana_family_sort_key(["arcane-affinity", "divine-mana"])
    dark = mana_family_sort_key(["dark-mana"])
    dark_divine = mana_family_sort_key(["dark-mana", "divine-affinity"])
    divine = mana_family_sort_key(["divine-mana"])

    assert arcane < arcane_dark < arcane_divine < dark < dark_divine < divine
    assert max(arcane, arcane_dark, arcane_divine, dark, dark_divine, divine) < (
        NO_MANA_FAMILY_SORT_KEY
    )
    assert mana_family_sort_key(["colorless-mana-3", "sola-affinity"]) == NO_MANA_FAMILY_SORT_KEY
