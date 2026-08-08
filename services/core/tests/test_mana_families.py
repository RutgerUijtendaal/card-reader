from card_reader_core.metadata import (
    MANA_FAMILIES,
    NO_MANA_FAMILY_SORT_KEY,
    mana_family_keys_for_symbol_keys,
    mana_family_sort_key,
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


def test_mana_and_affinity_aliases_resolve_to_one_family() -> None:
    assert mana_family_keys_for_symbol_keys(
        ["arcane-mana", "arcane-affinity", "dark-affinity"]
    ) == ("arcane", "dark")
    assert mana_family_sort_key(["arcane-mana", "arcane-affinity"]) == 0


def test_legacy_primal_affinity_alias_is_accepted_without_becoming_canonical() -> None:
    primal = MANA_FAMILIES[-1]

    assert mana_family_keys_for_symbol_keys(["primla-affinity"]) == ("primal",)
    assert mana_family_sort_key(["primla-affinity"]) == primal.rank
    assert primal.affinity_symbol_key == "primal-affinity"


def test_sort_keys_put_singles_before_lexicographic_multitypes_and_no_family_last() -> None:
    single_keys = [mana_family_sort_key([family.mana_symbol_key]) for family in MANA_FAMILIES]
    multi_keys = [
        mana_family_sort_key(["arcane-mana", "dark-affinity"]),
        mana_family_sort_key(["arcane-affinity", "dark-mana", "divine-mana"]),
        mana_family_sort_key(["arcane-mana", "divine-affinity"]),
        mana_family_sort_key(["dark-mana", "divine-affinity"]),
    ]

    assert single_keys == list(range(6))
    assert multi_keys == sorted(multi_keys)
    assert max(single_keys) < min(multi_keys)
    assert max(multi_keys) < NO_MANA_FAMILY_SORT_KEY
    assert mana_family_sort_key(["colorless-mana-3", "sola-affinity"]) == NO_MANA_FAMILY_SORT_KEY
