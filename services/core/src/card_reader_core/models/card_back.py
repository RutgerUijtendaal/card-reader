from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from django.conf import settings
from django.db import models

from .base import TimestampedModel, uuid_str
from .card import (
    CARD_FACTION_CHOICES,
    CARD_POOL_CHOICES,
    CARD_ROLE_CHOICES,
    CardFaction,
    CardPool,
    CardRole,
)

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.db.models.manager import Manager

    from .card import Card


class CardBackImportReceipt(TimestampedModel):
    """A used request key survives deletion of its immutable asset."""

    if TYPE_CHECKING:
        card_back_id: str | None
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    owner: models.ForeignKey[AbstractBaseUser, AbstractBaseUser] = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="card_back_imports"
    )
    client_request_id: models.UUIDField[UUID, UUID] = models.UUIDField()
    card_back: models.ForeignKey[CardBack | None, CardBack | None] = models.ForeignKey(
        "CardBack", on_delete=models.SET_NULL, null=True, related_name="import_receipts"
    )
    # Historical result, deliberately not an FK: a later merge/deletion must not rewrite it.
    hero_card_id: models.TextField[str | None, str | None] = models.TextField(null=True)
    error: models.TextField[str, str] = models.TextField(default="")

    class Meta:
        db_table = "card_back_import_receipt"
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "client_request_id"), name="ux_card_back_import_owner_key"
            )
        ]


class CardBack(TimestampedModel):
    if TYPE_CHECKING:
        card_overrides: Manager[Card]
        faction_defaults: Manager[CardBackFactionDefault]
        pool_defaults: Manager[CardBackPoolDefault]
        role_defaults: Manager[CardBackRoleDefault]
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


class CardBackRoleDefault(TimestampedModel):
    """Default card back for one persisted card role across every pool."""

    role: models.CharField[CardRole, CardRole] = models.CharField(
        max_length=64,
        choices=CARD_ROLE_CHOICES,
        primary_key=True,
    )
    card_back: models.ForeignKey[CardBack, CardBack] = models.ForeignKey(
        "CardBack",
        on_delete=models.PROTECT,
        related_name="role_defaults",
        db_column="card_back_id",
    )

    class Meta:
        db_table = "card_back_role_default"
