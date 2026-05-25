from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.db.models.manager import Manager

    from .card import Card


class CardGroup(TimestampedModel):
    if TYPE_CHECKING:
        members: Manager[CardGroupMember]

    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    name: models.TextField[str, str] = models.TextField(default="")
    anchor_card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.PROTECT,
        related_name="anchored_groups",
        db_column="anchor_card_id",
    )

    class Meta:
        db_table = "card_group"


class CardGroupMember(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    group: models.ForeignKey[CardGroup, CardGroup] = models.ForeignKey(
        "CardGroup",
        on_delete=models.CASCADE,
        related_name="members",
        db_column="group_id",
    )
    card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card",
        on_delete=models.CASCADE,
        related_name="card_group_memberships",
        db_column="card_id",
    )
    position: models.IntegerField[int, int] = models.IntegerField(default=1, db_index=True)

    class Meta:
        db_table = "card_group_member"
        constraints = [
            models.UniqueConstraint(fields=("group", "card"), name="ux_card_group_member_group_card"),
            models.UniqueConstraint(fields=("group", "position"), name="ux_card_group_member_group_position"),
        ]
        indexes = [models.Index(fields=["card", "position"], name="ix_card_group_member_card_position")]
