from __future__ import annotations

from django.db import models

from .base import TimestampedModel, uuid_str


class CardVersion(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_id: models.TextField[str, str] = models.TextField(db_index=True)
    version_number: models.IntegerField[int, int] = models.IntegerField(default=1, db_index=True)
    template_id: models.TextField[str, str] = models.TextField(db_index=True)
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
    is_latest: models.BooleanField[bool, bool] = models.BooleanField(default=True, db_index=True)
    previous_version_id: models.TextField[str | None, str | None] = models.TextField(
        default=None,
        null=True,
        db_index=True,
    )

    class Meta:
        db_table = "card_version"
        indexes = [models.Index(fields=["card_id", "is_latest"], name="ix_card_version_card_latest")]
        constraints = [
            models.UniqueConstraint(
                fields=("card_id", "version_number"),
                name="ux_card_version_card_version",
            )
        ]


class CardVersionImage(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version_id: models.TextField[str, str] = models.TextField(db_index=True)
    source_file: models.TextField[str, str] = models.TextField()
    stored_path: models.TextField[str, str] = models.TextField()
    width: models.IntegerField[int, int] = models.IntegerField(default=0)
    height: models.IntegerField[int, int] = models.IntegerField(default=0)
    checksum: models.TextField[str, str] = models.TextField(db_index=True)

    class Meta:
        db_table = "card_version_image"


class ParseResult(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version_id: models.TextField[str, str] = models.TextField(db_index=True)
    raw_ocr_json: models.TextField[str, str] = models.TextField()
    normalized_fields_json: models.TextField[str, str] = models.TextField()
    confidence_json: models.TextField[str, str] = models.TextField()

    class Meta:
        db_table = "parse_result"


