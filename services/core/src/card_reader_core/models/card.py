from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, cast

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


class Card(TimestampedModel):
    if TYPE_CHECKING:
        anchored_groups: Manager[CardGroup]
        card_group_memberships: Manager[CardGroupMember]
        aliases: Manager[CardAlias]
        merge_redirects: Manager[CardMergeRedirect]
        hero_decks: Manager[Deck]
        deck_entries: Manager[DeckEntry]
        deck_sideboard_entries: Manager[DeckSideboardEntry]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    is_hero: models.BooleanField[bool, bool] = models.BooleanField(default=False, db_index=True)
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


def normalize_card_lifecycle_filter(value: object) -> CardLifecycleFilter:
    if value in CARD_LIFECYCLE_FILTER_VALUES:
        return cast(CardLifecycleFilter, value)
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
    queryset: QuerySet,
    lifecycle_filter: CardLifecycleFilter = DEFAULT_CARD_LIFECYCLE_FILTER,
    *,
    field_path: str = "card__lifecycle_status",
) -> QuerySet:
    return queryset.filter(card_lifecycle_filter_q(lifecycle_filter, field_path=field_path))


class CardAlias(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.CASCADE,
        related_name="aliases",
        db_column="card_id",
    )
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")

    class Meta:
        db_table = "card_alias"


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


