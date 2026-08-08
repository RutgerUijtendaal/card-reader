from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class ManaFamilyDefinition:
    key: str
    label: str
    rank: int
    mana_symbol_key: str
    affinity_symbol_keys: tuple[str, ...]

    @property
    def affinity_symbol_key(self) -> str:
        return self.affinity_symbol_keys[0]

    @property
    def symbol_keys(self) -> tuple[str, ...]:
        return (self.mana_symbol_key, *self.affinity_symbol_keys)


_FAMILY_LABELS = (
    ("arcane", "Arcane"),
    ("dark", "Dark"),
    ("divine", "Divine"),
    ("martial", "Martial"),
    ("occult", "Occult"),
    ("primal", "Primal"),
)

MANA_FAMILIES: tuple[ManaFamilyDefinition, ...] = tuple(
    ManaFamilyDefinition(
        key=key,
        label=label,
        rank=rank,
        mana_symbol_key=f"{key}-mana",
        affinity_symbol_keys=(f"{key}-affinity", "primla-affinity") if key == "primal" else (f"{key}-affinity",),
    )
    for rank, (key, label) in enumerate(_FAMILY_LABELS)
)

MANA_FAMILY_BY_KEY = {family.key: family for family in MANA_FAMILIES}
MANA_FAMILY_BY_SYMBOL_KEY = {
    symbol_key: family
    for family in MANA_FAMILIES
    for symbol_key in family.symbol_keys
}

_SINGLE_FAMILY_RANKS = {(family.rank,): family.rank for family in MANA_FAMILIES}
_MULTI_FAMILY_COMBINATIONS = sorted(
    combination
    for size in range(2, len(MANA_FAMILIES) + 1)
    for combination in combinations(range(len(MANA_FAMILIES)), size)
)
_MULTI_FAMILY_RANKS = {
    combination: len(MANA_FAMILIES) + index
    for index, combination in enumerate(_MULTI_FAMILY_COMBINATIONS)
}
NO_MANA_FAMILY_SORT_KEY = len(MANA_FAMILIES) + len(_MULTI_FAMILY_COMBINATIONS)


def normalize_mana_family_keys(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    selected = {value.strip().casefold() for value in values if value.strip().casefold() in MANA_FAMILY_BY_KEY}
    return tuple(family.key for family in MANA_FAMILIES if family.key in selected)


def mana_family_keys_for_symbol_keys(symbol_keys: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    selected = {
        family.key
        for raw_key in symbol_keys
        if (family := MANA_FAMILY_BY_SYMBOL_KEY.get(raw_key.strip().casefold())) is not None
    }
    return tuple(family.key for family in MANA_FAMILIES if family.key in selected)


def mana_family_symbol_keys(family_keys: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        symbol_key
        for family_key in normalize_mana_family_keys(family_keys)
        for symbol_key in MANA_FAMILY_BY_KEY[family_key].symbol_keys
    )


def mana_family_sort_key(symbol_keys: list[str] | tuple[str, ...]) -> int:
    ranks = tuple(MANA_FAMILY_BY_KEY[key].rank for key in mana_family_keys_for_symbol_keys(symbol_keys))
    if len(ranks) == 1:
        return _SINGLE_FAMILY_RANKS[ranks]
    if len(ranks) > 1:
        return _MULTI_FAMILY_RANKS[ranks]
    return NO_MANA_FAMILY_SORT_KEY
