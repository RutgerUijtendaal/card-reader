from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, Literal, Protocol, TypeGuard, TypeVar

from django.db import models
from django.db.models import Q, QuerySet

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.db.models.manager import Manager

    from .card_group import CardGroup, CardGroupMember
    from .card_version import CardVersion
    from .deck import Deck, DeckEntry, DeckSideboardEntry


ACTIVE_CARD_LIFECYCLE_STATUS: Literal["active"] = "active"
DEPRECATED_CARD_LIFECYCLE_STATUS: Literal["deprecated"] = "deprecated"
ALL_CARD_LIFECYCLE_FILTER: Literal["all"] = "all"
CardLifecycleStatus = Literal["active", "deprecated"]
CardLifecycleFilter = Literal["active", "deprecated", "all"]

PLAYER_CARD_POOL: Literal["player"] = "player"
EVIL_CARD_POOL: Literal["evil"] = "evil"
NEUTRAL_CARD_POOL: Literal["neutral"] = "neutral"
CardPool = Literal["player", "evil", "neutral"]
DEFAULT_CARD_POOL: CardPool = PLAYER_CARD_POOL


@dataclass(frozen=True)
class CardPoolDefinition:
    key: CardPool
    label: str
    rank: int


CARD_POOL_DEFINITIONS: tuple[CardPoolDefinition, ...] = (
    CardPoolDefinition(key=PLAYER_CARD_POOL, label="Player", rank=0),
    CardPoolDefinition(key=EVIL_CARD_POOL, label="Evil", rank=1),
    CardPoolDefinition(key=NEUTRAL_CARD_POOL, label="Neutral", rank=2),
)
CARD_POOLS: tuple[CardPool, ...] = tuple(definition.key for definition in CARD_POOL_DEFINITIONS)
CARD_POOL_CHOICES: tuple[tuple[CardPool, str], ...] = tuple(
    (definition.key, definition.label) for definition in CARD_POOL_DEFINITIONS
)


@dataclass(frozen=True)
class CardPoolScope:
    """Explicit visibility boundary for card-derived reads and payloads."""

    allowed_pools: frozenset[CardPool]

    def __post_init__(self) -> None:
        normalized = frozenset(self.allowed_pools)
        invalid_pools = normalized.difference(CARD_POOLS)
        if invalid_pools:
            invalid = ", ".join(sorted(invalid_pools))
            raise ValueError(f"Unsupported card pool scope values: {invalid}.")
        object.__setattr__(self, "allowed_pools", normalized)

    def allows_card_pool(self, card_pool: str) -> bool:
        return card_pool in self.allowed_pools


PLAYER_CARD_POOL_SCOPE = CardPoolScope(frozenset({PLAYER_CARD_POOL}))
ALL_CARD_POOLS_SCOPE = CardPoolScope(frozenset(CARD_POOLS))

HERO_CARD_ROLE: Literal["hero"] = "hero"
BOSS_CARD_ROLE: Literal["boss"] = "boss"
BOON_CARD_ROLE: Literal["boon"] = "boon"
EVENT_CARD_ROLE: Literal["event"] = "event"
LOCATION_CARD_ROLE: Literal["location"] = "location"
SHOP_ITEM_CARD_ROLE: Literal["shop_item"] = "shop_item"
STANDARD_CARD_ROLE: Literal["standard"] = "standard"
CardRole = Literal["hero", "boss", "location", "boon", "event", "shop_item"]
CardRoleFilter = Literal[
    "standard",
    "hero",
    "boss",
    "location",
    "boon",
    "event",
    "shop_item",
]


@dataclass(frozen=True)
class CardRoleDefinition:
    key: CardRole
    label: str
    rank: int


@dataclass(frozen=True)
class CardRoleFilterDefinition:
    key: CardRoleFilter
    label: str
    rank: int
    derived: bool


CARD_ROLE_DEFINITIONS: tuple[CardRoleDefinition, ...] = (
    CardRoleDefinition(key=HERO_CARD_ROLE, label="Hero", rank=1),
    CardRoleDefinition(key=BOSS_CARD_ROLE, label="Boss", rank=2),
    CardRoleDefinition(key=LOCATION_CARD_ROLE, label="Location", rank=3),
    CardRoleDefinition(key=BOON_CARD_ROLE, label="Boon", rank=4),
    CardRoleDefinition(key=EVENT_CARD_ROLE, label="Event", rank=5),
    CardRoleDefinition(key=SHOP_ITEM_CARD_ROLE, label="Shop Item", rank=6),
)
CARD_ROLES: tuple[CardRole, ...] = tuple(definition.key for definition in CARD_ROLE_DEFINITIONS)
CARD_ROLE_CHOICES: tuple[tuple[CardRole, str], ...] = tuple(
    (definition.key, definition.label) for definition in CARD_ROLE_DEFINITIONS
)
CARD_ROLE_FILTER_VALUES: tuple[CardRoleFilter, ...] = (STANDARD_CARD_ROLE, *CARD_ROLES)
CARD_ROLE_FILTER_DEFINITIONS: tuple[CardRoleFilterDefinition, ...] = (
    CardRoleFilterDefinition(
        key=STANDARD_CARD_ROLE,
        label="Normal",
        rank=0,
        derived=True,
    ),
    *(
        CardRoleFilterDefinition(
            key=definition.key,
            label=definition.label,
            rank=definition.rank,
            derived=False,
        )
        for definition in CARD_ROLE_DEFINITIONS
    ),
)

ORDER_CARD_FACTION: Literal["order"] = "order"
BLOOD_CARD_FACTION: Literal["blood"] = "blood"
DARKNESS_CARD_FACTION: Literal["darkness"] = "darkness"
CardFaction = Literal["order", "blood", "darkness"]


@dataclass(frozen=True)
class CardFactionDefinition:
    key: CardFaction
    label: str
    rank: int


CARD_FACTION_DEFINITIONS: tuple[CardFactionDefinition, ...] = (
    CardFactionDefinition(key=ORDER_CARD_FACTION, label="Order", rank=1),
    CardFactionDefinition(key=BLOOD_CARD_FACTION, label="Blood", rank=2),
    CardFactionDefinition(key=DARKNESS_CARD_FACTION, label="Darkness", rank=3),
)
CARD_FACTIONS: tuple[CardFaction, ...] = tuple(
    definition.key for definition in CARD_FACTION_DEFINITIONS
)
CARD_FACTION_CHOICES: tuple[tuple[CardFaction, str], ...] = tuple(
    (definition.key, definition.label) for definition in CARD_FACTION_DEFINITIONS
)


class CardLifecycleCarrier(Protocol):
    lifecycle_status: str


CARD_LIFECYCLE_STATUSES: tuple[CardLifecycleStatus, ...] = (
    ACTIVE_CARD_LIFECYCLE_STATUS,
    DEPRECATED_CARD_LIFECYCLE_STATUS,
)
CARD_LIFECYCLE_FILTER_VALUES: tuple[CardLifecycleFilter, ...] = (
    *CARD_LIFECYCLE_STATUSES,
    ALL_CARD_LIFECYCLE_FILTER,
)
DEFAULT_CARD_LIFECYCLE_FILTER: CardLifecycleFilter = ACTIVE_CARD_LIFECYCLE_STATUS
_ModelT = TypeVar("_ModelT", bound=models.Model)


class Card(TimestampedModel):
    if TYPE_CHECKING:
        anchored_groups: Manager[CardGroup]
        card_group_memberships: Manager[CardGroupMember]
        aliases: Manager[CardAlias]
        merge_redirects: Manager[CardMergeRedirect]
        hero_decks: Manager[Deck]
        deck_entries: Manager[DeckEntry]
        deck_sideboard_entries: Manager[DeckSideboardEntry]
        role_assignments: Manager[CardRoleAssignment]
        faction_assignments: Manager[CardFactionAssignment]
        versions: Manager[CardVersion]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True)
    label: models.TextField[str, str] = models.TextField(default="")
    card_pool: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=CARD_POOL_CHOICES,
        default=DEFAULT_CARD_POOL,
        db_index=True,
    )
    faction_identity_key: models.TextField[str, str] = models.TextField(
        default="[]",
        editable=False,
    )
    deck_building_config_json = models.JSONField(default=dict)
    lifecycle_status: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[
            (ACTIVE_CARD_LIFECYCLE_STATUS, "Active"),
            (DEPRECATED_CARD_LIFECYCLE_STATUS, "Deprecated"),
        ],
        default=ACTIVE_CARD_LIFECYCLE_STATUS,
        db_index=True,
    )
    latest_version: models.ForeignKey[CardVersion | None, CardVersion | None] = models.ForeignKey(
        "CardVersion",
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="latest_version_id",
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "card"
        constraints = [
            models.UniqueConstraint(
                fields=("card_pool", "faction_identity_key", "key"),
                name="uq_card_pool_faction_key",
            ),
        ]


class CardIdentityPoolLock(TimestampedModel):
    """Durable serialization row for card primary/alias namespace mutations."""

    card_pool: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=CARD_POOL_CHOICES,
        primary_key=True,
    )
    revision: models.PositiveBigIntegerField[int, int] = models.PositiveBigIntegerField(default=0)

    class Meta:
        db_table = "card_identity_pool_lock"


class CardRoleAssignment(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.CASCADE,
        related_name="role_assignments",
        db_column="card_id",
    )
    role: models.CharField[str, str] = models.CharField(
        max_length=64,
        choices=CARD_ROLE_CHOICES,
        db_index=True,
    )

    class Meta:
        db_table = "card_role_assignment"
        constraints = [
            models.UniqueConstraint(fields=("card", "role"), name="uq_card_role_assignment_card_role"),
        ]


class CardFactionAssignment(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.CASCADE,
        related_name="faction_assignments",
        db_column="card_id",
    )
    faction: models.CharField[str, str] = models.CharField(
        max_length=64,
        choices=CARD_FACTION_CHOICES,
        db_index=True,
    )

    class Meta:
        db_table = "card_faction_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=("card", "faction"),
                name="uq_card_faction_assignment_card_faction",
            ),
        ]


def is_card_pool(value: object) -> TypeGuard[CardPool]:
    return value in CARD_POOLS


def normalize_card_roles(values: Iterable[object]) -> tuple[CardRole, ...]:
    requested = set(values)
    return tuple(role for role in CARD_ROLES if role in requested)


def normalize_card_factions(values: Iterable[object]) -> tuple[CardFaction, ...]:
    requested = set(values)
    return tuple(faction for faction in CARD_FACTIONS if faction in requested)


def card_faction_identity_key(values: Iterable[object]) -> str:
    return json.dumps(normalize_card_factions(values), separators=(",", ":"))


def card_role_keys(card: Card) -> tuple[CardRole, ...]:
    prefetched = getattr(card, "_prefetched_objects_cache", {}).get("role_assignments")
    assignments = prefetched if prefetched is not None else card.role_assignments.all()
    return normalize_card_roles(assignment.role for assignment in assignments)


def card_has_role(card: Card, role: CardRole) -> bool:
    prefetched = getattr(card, "_prefetched_objects_cache", {}).get("role_assignments")
    if prefetched is not None:
        return any(assignment.role == role for assignment in prefetched)
    return card.role_assignments.filter(role=role).exists()


def card_faction_keys(card: Card) -> tuple[CardFaction, ...]:
    prefetched = getattr(card, "_prefetched_objects_cache", {}).get("faction_assignments")
    assignments = prefetched if prefetched is not None else card.faction_assignments.all()
    return normalize_card_factions(assignment.faction for assignment in assignments)


def card_has_faction(card: Card, faction: CardFaction) -> bool:
    prefetched = getattr(card, "_prefetched_objects_cache", {}).get("faction_assignments")
    if prefetched is not None:
        return any(assignment.faction == faction for assignment in prefetched)
    return card.faction_assignments.filter(faction=faction).exists()


def normalize_card_lifecycle_filter(value: object) -> CardLifecycleFilter:
    if value in CARD_LIFECYCLE_FILTER_VALUES:
        return value
    return DEFAULT_CARD_LIFECYCLE_FILTER


def is_card_lifecycle_status(value: object) -> bool:
    return value in CARD_LIFECYCLE_STATUSES


def card_is_deprecated(card: CardLifecycleCarrier) -> bool:
    return card.lifecycle_status == DEPRECATED_CARD_LIFECYCLE_STATUS


def card_is_visible_for_lifecycle(card: CardLifecycleCarrier, lifecycle_filter: CardLifecycleFilter) -> bool:
    return lifecycle_filter == ALL_CARD_LIFECYCLE_FILTER or card.lifecycle_status == lifecycle_filter


def card_lifecycle_filter_q(
    lifecycle_filter: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
    *,
    field_path: str = "card__lifecycle_status",
) -> Q:
    normalized = normalize_card_lifecycle_filter(lifecycle_filter)
    if normalized == ALL_CARD_LIFECYCLE_FILTER:
        return Q()
    return Q(**{field_path: normalized})


def active_card_lifecycle_q(*, field_path: str = "card__lifecycle_status") -> Q:
    return card_lifecycle_filter_q(ACTIVE_CARD_LIFECYCLE_STATUS, field_path=field_path)


def filter_queryset_by_card_lifecycle(
    queryset: QuerySet[_ModelT],
    lifecycle_filter: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
    *,
    field_path: str = "card__lifecycle_status",
) -> QuerySet[_ModelT]:
    return queryset.filter(card_lifecycle_filter_q(lifecycle_filter, field_path=field_path))


class CardAlias(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.CASCADE,
        related_name="aliases",
        db_column="card_id",
    )
    card_pool: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=CARD_POOL_CHOICES,
        db_index=True,
    )
    faction_identity_key: models.TextField[str, str] = models.TextField(
        default="[]",
        editable=False,
    )
    key: models.TextField[str, str] = models.TextField(default="", db_index=True)
    label: models.TextField[str, str] = models.TextField(default="")

    class Meta:
        db_table = "card_alias"
        constraints = [
            models.UniqueConstraint(
                fields=("card_pool", "faction_identity_key", "key"),
                name="uq_card_alias_pool_faction_key",
            ),
        ]


class CardMergeRedirect(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    old_card_id: models.TextField[str, str] = models.TextField(db_index=True, unique=True)
    target_card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.CASCADE,
        related_name="merge_redirects",
        db_column="target_card_id",
    )

    class Meta:
        db_table = "card_merge_redirect"


