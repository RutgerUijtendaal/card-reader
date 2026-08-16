from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from card_reader_core.models import (
    DEFAULT_CARD_LIFECYCLE_FILTER as CORE_DEFAULT_CARD_LIFECYCLE_FILTER,
    CardLifecycleFilter as CoreCardLifecycleFilter,
    CardFaction,
    CardPool,
    CardRole,
    CardRoleFilter,
    CardVersion,
    CardVersionImage,
    Keyword,
    Symbol,
    Tag,
    Type,
)
from card_reader_core.metadata import ManaFamily

CardSort = Literal[
    "default",
    "updated_desc",
    "name_asc",
    "mana_asc",
    "mana_desc",
    "mana_type_asc",
    "types_asc",
]
CardLifecycleFilter = CoreCardLifecycleFilter
CardRoleMatch = Literal["any", "all"]
CARD_SORT_DEFAULT: CardSort = "default"
CARD_SORT_UPDATED_DESC: CardSort = "updated_desc"
CARD_SORT_NAME_ASC: CardSort = "name_asc"
CARD_SORT_MANA_ASC: CardSort = "mana_asc"
CARD_SORT_MANA_DESC: CardSort = "mana_desc"
CARD_SORT_MANA_TYPE_ASC: CardSort = "mana_type_asc"
CARD_SORT_TYPES_ASC: CardSort = "types_asc"
CARD_SORT_VALUES: tuple[CardSort, ...] = (
    CARD_SORT_DEFAULT,
    CARD_SORT_UPDATED_DESC,
    CARD_SORT_NAME_ASC,
    CARD_SORT_MANA_ASC,
    CARD_SORT_MANA_DESC,
    CARD_SORT_MANA_TYPE_ASC,
    CARD_SORT_TYPES_ASC,
)
DEFAULT_CARD_PAGE_SIZE = 36
DEFAULT_CARD_LIFECYCLE_FILTER = CORE_DEFAULT_CARD_LIFECYCLE_FILTER


@dataclass(frozen=True)
class LatestCardVersionReparseSource:
    card_id: str
    card_version_id: str
    template_id: str
    image_path: Path
    card_pool: CardPool
    card_roles: tuple[CardRole, ...]
    card_factions: tuple[CardFaction, ...]
    card_mana_families: tuple[ManaFamily, ...]


@dataclass(frozen=True)
class CardListRow:
    version: CardVersion
    image: CardVersionImage | None
    keywords: list[Keyword]
    tags: list[Tag]
    symbols: list[Symbol]
    types: list[Type]


@dataclass(frozen=True)
class CardImageSource:
    card_id: str
    card_version_id: str
    checksum: str
    path: Path


@dataclass(frozen=True)
class CardListCandidate:
    version: CardVersion
    types: list[Type]


@dataclass(frozen=True)
class PaginatedCardList:
    count: int
    page: int
    page_size: int
    results: list[CardListRow]


class CardFilterParams(TypedDict):
    query: str | None
    card_ids: list[str] | None
    max_confidence: float | None
    keyword_ids: list[str] | None
    keyword_match: str | None
    tag_ids: list[str] | None
    tag_match: str | None
    mana_symbol_ids: list[str] | None
    mana_symbol_exclude_ids: list[str] | None
    mana_symbol_match: str | None
    mana_family_keys: list[str] | None
    mana_family_exclude_keys: list[str] | None
    mana_family_match: str | None
    affinity_symbol_ids: list[str] | None
    affinity_symbol_exclude_ids: list[str] | None
    affinity_symbol_match: str | None
    devotion_symbol_ids: list[str] | None
    devotion_symbol_exclude_ids: list[str] | None
    devotion_symbol_match: str | None
    other_symbol_ids: list[str] | None
    other_symbol_exclude_ids: list[str] | None
    other_symbol_match: str | None
    symbol_ids: list[str] | None
    type_ids: list[str] | None
    type_exclude_ids: list[str] | None
    type_match: str | None
    mana_cost_min: int | None
    mana_cost_max: int | None
    template_id: str | None
    card_pool: CardPool
    card_roles: list[CardRoleFilter] | None
    card_role_exclude: list[CardRoleFilter] | None
    card_role_match: CardRoleMatch
    card_factions: list[CardFaction] | None
    card_faction_exclude: list[CardFaction] | None
    card_faction_match: CardRoleMatch
    attack_min: int | None
    attack_max: int | None
    health_min: int | None
    health_max: int | None
    lifecycle_status: CardLifecycleFilter
    sort: CardSort


@dataclass(frozen=True)
class ParsedCardSaveResult:
    version: CardVersion
    created_new_version: bool


class FieldSourcesPayload(TypedDict):
    fields: dict[str, str]
    metadata: dict[str, str]


class ParsedSnapshotPayload(TypedDict):
    fields: dict[str, object]
    metadata: dict[str, list[str]]


class CardIdentityConflict(ValueError):
    """A primary name or alias collides inside one pool/faction namespace."""
