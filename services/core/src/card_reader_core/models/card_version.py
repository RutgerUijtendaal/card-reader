from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from .card import Card
    from .template import Template


class CardVersion(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card: models.ForeignKey[Card, Card] = models.ForeignKey(
        "Card", on_delete=models.CASCADE, related_name="versions", db_column="card_id"
    )
    version_number: models.IntegerField[int, int] = models.IntegerField(default=1, db_index=True)
    template: models.ForeignKey[Template, Template] = models.ForeignKey(
        "Template",
        on_delete=models.PROTECT,
        related_name="card_versions",
        db_column="template_id",
        to_field="key",
    )
    image_hash: models.TextField[str, str] = models.TextField(db_index=True)
    name: models.TextField[str, str] = models.TextField(default="")
    type_line: models.TextField[str, str] = models.TextField(default="")
    mana_cost: models.TextField[str, str] = models.TextField(default="")
    mana_symbols_json: models.TextField[str, str] = models.TextField(default="[]")
    attack: models.IntegerField[int | None, int | None] = models.IntegerField(default=None, null=True)
    health: models.IntegerField[int | None, int | None] = models.IntegerField(default=None, null=True)
    rules_text: models.TextField[str, str] = models.TextField(default="")
    confidence: models.FloatField[float, float] = models.FloatField(default=0.0)
    parse_result_id: models.TextField[str | None, str | None] = models.TextField(
        default=None,
        null=True,
        db_index=True,
    )
    field_sources_json: models.TextField[str, str] = models.TextField(default="{}")
    parsed_snapshot_json: models.TextField[str, str] = models.TextField(default="{}")
    is_latest: models.BooleanField[bool, bool] = models.BooleanField(default=True, db_index=True)
    previous_version: models.ForeignKey[CardVersion | None, CardVersion | None] = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="next_versions",
        db_column="previous_version_id",
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "card_version"
        indexes = [models.Index(fields=["card", "is_latest"], name="ix_card_version_card_latest")]
        constraints = [
            models.UniqueConstraint(
                fields=("card", "version_number"),
                name="ux_card_version_card_version",
            )
        ]


class CardVersionImage(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version: models.ForeignKey[CardVersion, CardVersion] = models.ForeignKey(
        "CardVersion",
        on_delete=models.CASCADE,
        related_name="images",
        db_column="card_version_id",
    )
    source_file: models.TextField[str, str] = models.TextField()
    stored_path: models.TextField[str, str] = models.TextField()
    width: models.IntegerField[int, int] = models.IntegerField(default=0)
    height: models.IntegerField[int, int] = models.IntegerField(default=0)
    checksum: models.TextField[str, str] = models.TextField(db_index=True)

    class Meta:
        db_table = "card_version_image"


class ParseResult(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version: models.ForeignKey[CardVersion, CardVersion] = models.ForeignKey(
        "CardVersion",
        on_delete=models.CASCADE,
        related_name="parse_results",
        db_column="card_version_id",
    )
    raw_ocr_json: models.TextField[str, str] = models.TextField()
    normalized_fields_json: models.TextField[str, str] = models.TextField()
    confidence_json: models.TextField[str, str] = models.TextField()

    class Meta:
        db_table = "parse_result"


