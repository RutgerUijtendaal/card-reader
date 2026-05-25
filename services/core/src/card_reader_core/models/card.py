from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.db.models.manager import Manager

    from .card_group import CardGroup, CardGroupMember
    from .card_version import CardVersion
    from .deck import Deck, DeckEntry


class Card(TimestampedModel):
    if TYPE_CHECKING:
        anchored_groups: Manager[CardGroup]
        card_group_memberships: Manager[CardGroupMember]
        hero_decks: Manager[Deck]
        deck_entries: Manager[DeckEntry]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    is_hero: models.BooleanField[bool, bool] = models.BooleanField(default=False, db_index=True)
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


