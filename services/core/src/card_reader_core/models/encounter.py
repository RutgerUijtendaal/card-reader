from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from django.conf import settings
from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.db.models.manager import Manager
    from django.contrib.auth.models import AbstractBaseUser
    from .card import Card
    from .card_group import CardGroup


class Encounter(TimestampedModel):
    if TYPE_CHECKING:
        entries: Manager[EncounterEntry]
        boss_card_id: str | None
        boss_group_id: str | None
        creator_id: int

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    creator: models.ForeignKey[AbstractBaseUser, AbstractBaseUser] = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="encounters"
    )
    name: models.TextField[str, str] = models.TextField(default="", blank=True)
    description_markup: models.TextField[str, str] = models.TextField(default="", blank=True)
    description: models.TextField[str, str] = models.TextField(default="", blank=True)
    long_description_markup: models.TextField[str, str] = models.TextField(default="", blank=True)
    long_description: models.TextField[str, str] = models.TextField(default="", blank=True)
    boss_card: models.ForeignKey[Card | None, Card | None] = models.ForeignKey(
        "Card", null=True, blank=True, on_delete=models.PROTECT, related_name="boss_encounters"
    )
    boss_group: models.ForeignKey[CardGroup | None, CardGroup | None] = models.ForeignKey(
        "CardGroup", null=True, blank=True, on_delete=models.PROTECT, related_name="encounters"
    )
    factions = models.JSONField(default=list)
    visibility: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[("private", "Staff only"), ("public", "Public")],
        default="private",
        db_index=True,
    )
    revision: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "encounter"
        ordering = ["-created_at", "id"]


class EncounterEntry(TimestampedModel):
    if TYPE_CHECKING:
        card_id: str

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    encounter: models.ForeignKey[Encounter, Encounter] = models.ForeignKey(
        Encounter, on_delete=models.CASCADE, related_name="entries"
    )
    card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card", on_delete=models.PROTECT, related_name="encounter_entries"
    )
    quantity: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(default=1)
    position: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "encounter_entry"
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["encounter", "card"], name="ux_encounter_entry_card"),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="ck_encounter_entry_quantity"
            ),
        ]


class EncounterCreation(TimestampedModel):
    if TYPE_CHECKING:
        encounter_id: str | None

    creator: models.ForeignKey[AbstractBaseUser, AbstractBaseUser] = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    client_creation_id: models.UUIDField[UUID, UUID] = models.UUIDField()
    encounter: models.OneToOneField[Encounter | None, Encounter | None] = models.OneToOneField(
        Encounter, null=True, on_delete=models.SET_NULL
    )

    class Meta:
        db_table = "encounter_creation"
        constraints = [
            models.UniqueConstraint(
                fields=["creator", "client_creation_id"], name="ux_encounter_creation_key"
            )
        ]
