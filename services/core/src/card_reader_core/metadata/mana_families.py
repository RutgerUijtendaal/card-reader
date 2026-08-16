from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Literal


ManaFamily = Literal["arcane", "dark", "divine", "martial", "occult", "primal"]


@dataclass(frozen=True)
class ManaFamilyDefinition:
    key: ManaFamily
    label: str
    rank: int
    mana_symbol_key: str
    affinity_symbol_keys: tuple[str, ...]

    @property
    def affinity_symbol_key(self) -> str:
        return self.affinity_symbol_keys[0]

    @property
    def display_symbol_key(self) -> str:
        return self.mana_symbol_key

    @property
    def symbol_keys(self) -> tuple[str, ...]:
        return (self.mana_symbol_key, *self.affinity_symbol_keys)


_FAMILY_LABELS: tuple[tuple[ManaFamily, str], ...] = (
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
MANA_FAMILY_CHOICES: tuple[tuple[ManaFamily, str], ...] = tuple(
    (family.key, family.label) for family in MANA_FAMILIES
)
MANA_FAMILY_BY_SYMBOL_KEY = {
    symbol_key: family
    for family in MANA_FAMILIES
    for symbol_key in family.symbol_keys
}

_FAMILY_COMBINATIONS = sorted(
    (
        combination
        for size in range(1, len(MANA_FAMILIES) + 1)
        for combination in combinations(range(len(MANA_FAMILIES)), size)
    ),
    key=lambda combination: (
        combination[0],
        sum(1 << rank for rank in combination),
    ),
)
_FAMILY_COMBINATION_RANKS = {
    combination: index for index, combination in enumerate(_FAMILY_COMBINATIONS)
}
NO_MANA_FAMILY_SORT_KEY = len(_FAMILY_COMBINATIONS)


def normalize_mana_family_keys(values: list[str] | tuple[str, ...]) -> tuple[ManaFamily, ...]:
    selected = {value.strip().casefold() for value in values if value.strip().casefold() in MANA_FAMILY_BY_KEY}
    return tuple(family.key for family in MANA_FAMILIES if family.key in selected)


def mana_family_keys_for_symbol_keys(
    symbol_keys: list[str] | tuple[str, ...],
) -> tuple[ManaFamily, ...]:
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


def mana_family_sort_key_for_family_keys(family_keys: list[str] | tuple[str, ...]) -> int:
    ranks = tuple(MANA_FAMILY_BY_KEY[key].rank for key in normalize_mana_family_keys(family_keys))
    return _FAMILY_COMBINATION_RANKS.get(ranks, NO_MANA_FAMILY_SORT_KEY)


def mana_family_sort_key(symbol_keys: list[str] | tuple[str, ...]) -> int:
    """Return the legacy symbol-derived key used by compatibility imports."""
    return mana_family_sort_key_for_family_keys(mana_family_keys_for_symbol_keys(symbol_keys))
