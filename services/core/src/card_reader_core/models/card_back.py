from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from .base import TimestampedModel, uuid_str
from .card import CARD_FACTION_CHOICES, CARD_POOL_CHOICES, CardFaction, CardPool

if TYPE_CHECKING:
    from django.db.models.manager import Manager

    from .card import Card


class CardBack(TimestampedModel):
    if TYPE_CHECKING:
        card_overrides: Manager[Card]
        faction_defaults: Manager[CardBackFactionDefault]
        pool_defaults: Manager[CardBackPoolDefault]
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    label: models.TextField[str, str] = models.TextField(default="")
    original_filename: models.TextField[str, str] = models.TextField(default="")
    source_file: models.TextField[str, str] = models.TextField()
    stored_path: models.TextField[str, str] = models.TextField(db_index=True)
    width: models.IntegerField[int, int] = models.IntegerField(default=0)
    height: models.IntegerField[int, int] = models.IntegerField(default=0)
    checksum: models.TextField[str, str] = models.TextField(db_index=True)

    class Meta:
        db_table = "card_back"
        ordering = ["-created_at", "-id"]


class CardBackPoolDefault(TimestampedModel):
    card_pool: models.CharField[CardPool, CardPool] = models.CharField(
        max_length=16,
        choices=CARD_POOL_CHOICES,
        primary_key=True,
    )
    card_back: models.ForeignKey[CardBack, CardBack] = models.ForeignKey(
        "CardBack",
        on_delete=models.PROTECT,
        related_name="pool_defaults",
        db_column="card_back_id",
    )

    class Meta:
        db_table = "card_back_pool_default"


class CardBackFactionDefault(TimestampedModel):
    """Default card back for one faction within the Evil card pool."""

    faction: models.CharField[CardFaction, CardFaction] = models.CharField(
        max_length=64,
        choices=CARD_FACTION_CHOICES,
        primary_key=True,
    )
    card_back: models.ForeignKey[CardBack, CardBack] = models.ForeignKey(
        "CardBack",
        on_delete=models.PROTECT,
        related_name="faction_defaults",
        db_column="card_back_id",
    )

    class Meta:
        db_table = "card_back_faction_default"
