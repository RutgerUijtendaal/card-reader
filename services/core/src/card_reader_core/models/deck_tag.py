from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.db.models.manager import Manager

    from .deck import Deck


DECK_TAG_KINDS = ("role", "type")
DECK_TAG_SUGGESTION_STATUSES = ("pending", "accepted", "rejected")

DeckTagKind = Literal["role", "type"]
DeckTagSuggestionStatus = Literal["pending", "accepted", "rejected"]


class DeckTag(TimestampedModel):
    if TYPE_CHECKING:
        assignments: Manager[DeckTagAssignment]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    kind: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[("role", "Role"), ("type", "Type")],
        db_index=True,
    )
    key: models.TextField[str, str] = models.TextField(default="", db_index=True)
    label: models.TextField[str, str] = models.TextField(default="")

    class Meta:
        db_table = "deck_tag"
        ordering = ["kind", "label", "id"]
        constraints = [
            models.UniqueConstraint(fields=("kind", "key"), name="ux_deck_tag_kind_key"),
        ]


class DeckTagAssignment(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    deck: models.ForeignKey[Deck, Deck] = models.ForeignKey(
        "Deck",
        on_delete=models.CASCADE,
        related_name="tag_assignments",
        db_column="deck_id",
    )
    tag: models.ForeignKey[DeckTag, DeckTag] = models.ForeignKey(
        "DeckTag",
        on_delete=models.CASCADE,
        related_name="assignments",
        db_column="tag_id",
    )

    class Meta:
        db_table = "deck_tag_assignment"
        ordering = ["tag__kind", "tag__label", "id"]
        constraints = [
            models.UniqueConstraint(fields=("deck", "tag"), name="ux_deck_tag_assignment_pair"),
        ]
        indexes = [models.Index(fields=["tag", "deck"], name="ix_deck_tag_assignment_tag")]


class DeckTagSuggestion(TimestampedModel):
    if TYPE_CHECKING:
        deck_occurrences: Manager[DeckTagSuggestionDeck]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    kind: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[("type", "Type")],
        default="type",
        db_index=True,
    )
    normalized_value: models.TextField[str, str] = models.TextField(default="", db_index=True)
    display_value: models.TextField[str, str] = models.TextField(default="")
    status: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")],
        default="pending",
        db_index=True,
    )
    accepted_tag: models.ForeignKey[DeckTag | None, DeckTag | None] = models.ForeignKey(
        "DeckTag",
        on_delete=models.SET_NULL,
        related_name="accepted_suggestions",
        db_column="accepted_tag_id",
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "deck_tag_suggestion"
        ordering = ["status", "display_value", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=("kind", "normalized_value"),
                name="ux_deck_tag_suggestion_kind_value",
            ),
        ]


class DeckTagSuggestionDeck(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    suggestion: models.ForeignKey[DeckTagSuggestion, DeckTagSuggestion] = models.ForeignKey(
        "DeckTagSuggestion",
        on_delete=models.CASCADE,
        related_name="deck_occurrences",
        db_column="suggestion_id",
    )
    deck: models.ForeignKey[Deck, Deck] = models.ForeignKey(
        "Deck",
        on_delete=models.CASCADE,
        related_name="tag_suggestion_occurrences",
        db_column="deck_id",
    )

    class Meta:
        db_table = "deck_tag_suggestion_deck"
        constraints = [
            models.UniqueConstraint(
                fields=("suggestion", "deck"),
                name="ux_deck_tag_suggestion_deck_pair",
            ),
        ]
        indexes = [models.Index(fields=["deck", "suggestion"], name="ix_deck_tag_suggestion_deck")]
