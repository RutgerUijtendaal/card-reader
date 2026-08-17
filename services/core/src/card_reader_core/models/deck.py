from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from django.conf import settings
from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from django.db.models.manager import Manager

    from .card import Card
    from .deck_tag import DeckTagAssignment, DeckTagSuggestionDeck


class Deck(TimestampedModel):
    if TYPE_CHECKING:
        entries: Manager[DeckEntry]
        sideboards: Manager[DeckSideboard]
        tag_assignments: Manager[DeckTagAssignment]
        tag_suggestion_occurrences: Manager[DeckTagSuggestionDeck]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    owner: models.ForeignKey[AbstractBaseUser, AbstractBaseUser] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="decks",
        db_column="owner_id",
    )
    name: models.TextField[str, str] = models.TextField(default="")
    description_markup: models.TextField[str | None, str | None] = models.TextField(
        default=None, null=True, blank=True
    )
    description: models.TextField[str | None, str | None] = models.TextField(default=None, null=True, blank=True)
    long_description_markup: models.TextField[str | None, str | None] = models.TextField(
        default=None, null=True, blank=True
    )
    long_description: models.TextField[str | None, str | None] = models.TextField(default=None, null=True, blank=True)
    difficulty: models.CharField[str | None, str | None] = models.CharField(
        max_length=16,
        choices=[
            ("easy", "Easy"),
            ("medium", "Medium"),
            ("hard", "Hard"),
        ],
        default=None,
        null=True,
        blank=True,
    )
    visibility: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[
            ("private", "Private"),
            ("unlisted", "Unlisted"),
            ("public", "Public"),
        ],
        default="private",
        db_index=True,
    )
    hero_card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.PROTECT,
        related_name="hero_decks",
        db_column="hero_card_id",
    )
    client_creation_id: models.UUIDField[UUID | None, UUID | None] = models.UUIDField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "deck"
        indexes = [models.Index(fields=["owner", "updated_at"], name="ix_deck_owner_updated")]
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "client_creation_id"),
                name="ux_deck_owner_creation_id",
            )
        ]


class DeckCreation(TimestampedModel):
    if TYPE_CHECKING:
        deck_id: str | None

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    owner: models.ForeignKey[AbstractBaseUser, AbstractBaseUser] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deck_creations",
        db_column="owner_id",
    )
    client_creation_id: models.UUIDField[UUID, UUID] = models.UUIDField()
    deck: models.OneToOneField[Deck | None, Deck | None] = models.OneToOneField(
        "Deck",
        on_delete=models.SET_NULL,
        related_name="creation_record",
        db_column="deck_id",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "deck_creation"
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "client_creation_id"),
                name="ux_deck_creation_owner_key",
            )
        ]


DeckVisibility = Literal["private", "unlisted", "public"]
DeckDifficulty = Literal["easy", "medium", "hard"]


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
    position: models.IntegerField[int, int] = models.IntegerField(default=0)

    class Meta:
        db_table = "deck_entry"
        ordering = ["position", "card_id"]
        constraints = [models.UniqueConstraint(fields=("deck", "card"), name="ux_deck_entry_deck_card")]
        indexes = [
            models.Index(fields=["deck", "created_at"], name="ix_deck_entry_deck_created"),
            models.Index(fields=["deck", "position"], name="ix_deck_entry_deck_pos"),
        ]


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
    position: models.IntegerField[int, int] = models.IntegerField(default=0)

    class Meta:
        db_table = "deck_sideboard_entry"
        ordering = ["position", "card_id"]
        constraints = [models.UniqueConstraint(fields=("sideboard", "card"), name="ux_deck_sideboard_entry_card")]
        indexes = [
            models.Index(fields=["sideboard", "created_at"], name="ix_sideboard_entry_created"),
            models.Index(fields=["sideboard", "position"], name="ix_deck_side_entry_pos"),
        ]
