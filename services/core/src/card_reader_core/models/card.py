from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.db.models.manager import Manager

    from .card_group import CardGroup, CardGroupMember
    from .card_version import CardVersion
    from .deck import Deck, DeckEntry, DeckSideboardEntry


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
            ("active", "Active"),
            ("deprecated", "Deprecated"),
        ],
        default="active",
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


CardLifecycleStatus = Literal["active", "deprecated"]


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


