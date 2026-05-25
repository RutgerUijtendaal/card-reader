from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from django.db.models.manager import Manager

    from .card import Card


class Deck(TimestampedModel):
    if TYPE_CHECKING:
        entries: Manager[DeckEntry]
        sideboards: Manager[DeckSideboard]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    owner: models.ForeignKey[AbstractBaseUser, AbstractBaseUser] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="decks",
        db_column="owner_id",
    )
    name: models.TextField[str, str] = models.TextField(default="")
    description: models.TextField[str | None, str | None] = models.TextField(default=None, null=True, blank=True)
    is_public: models.BooleanField[bool, bool] = models.BooleanField(default=False, db_index=True)
    hero_card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.PROTECT,
        related_name="hero_decks",
        db_column="hero_card_id",
    )

    class Meta:
        db_table = "deck"
        indexes = [models.Index(fields=["owner", "updated_at"], name="ix_deck_owner_updated")]


class DeckEntry(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    deck: models.ForeignKey[Deck, Deck] = models.ForeignKey(
        "Deck",
        on_delete=models.CASCADE,
        related_name="entries",
        db_column="deck_id",
    )
    card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.CASCADE,
        related_name="deck_entries",
        db_column="card_id",
    )
    quantity: models.IntegerField[int, int] = models.IntegerField(default=1)

    class Meta:
        db_table = "deck_entry"
        constraints = [models.UniqueConstraint(fields=("deck", "card"), name="ux_deck_entry_deck_card")]
        indexes = [models.Index(fields=["deck", "created_at"], name="ix_deck_entry_deck_created")]


class DeckSideboard(TimestampedModel):
    if TYPE_CHECKING:
        entries: Manager[DeckSideboardEntry]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    deck: models.ForeignKey[Deck, Deck] = models.ForeignKey(
        "Deck",
        on_delete=models.CASCADE,
        related_name="sideboards",
        db_column="deck_id",
    )
    name: models.TextField[str, str] = models.TextField(default="")

    class Meta:
        db_table = "deck_sideboard"
        indexes = [
            models.Index(fields=["deck", "created_at"], name="ix_deck_sideboard_deck_created"),
        ]


class DeckSideboardEntry(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    sideboard: models.ForeignKey[DeckSideboard, DeckSideboard] = models.ForeignKey(
        "DeckSideboard",
        on_delete=models.CASCADE,
        related_name="entries",
        db_column="sideboard_id",
    )
    card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.CASCADE,
        related_name="deck_sideboard_entries",
        db_column="card_id",
    )
    quantity: models.IntegerField[int, int] = models.IntegerField(default=1)

    class Meta:
        db_table = "deck_sideboard_entry"
        constraints = [models.UniqueConstraint(fields=("sideboard", "card"), name="ux_deck_sideboard_entry_card")]
        indexes = [models.Index(fields=["sideboard", "created_at"], name="ix_deck_sideboard_entry_created")]
