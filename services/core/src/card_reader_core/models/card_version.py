from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from django.db.models.manager import Manager

    from .card import Card
    from .metadata import (
        CardVersionKeyword,
        CardVersionMetadataSuggestion,
        CardVersionSymbol,
        CardVersionTag,
        CardVersionType,
    )
    from .content_version import ContentVersion
    from .template import Template


class CardVersion(TimestampedModel):
    if TYPE_CHECKING:
        images: Manager[CardVersionImage]
        parse_results: Manager[ParseResult]
        card_version_keywords: Manager[CardVersionKeyword]
        card_version_tags: Manager[CardVersionTag]
        card_version_symbols: Manager[CardVersionSymbol]
        card_version_types: Manager[CardVersionType]
        card_version_metadata_suggestions: Manager[CardVersionMetadataSuggestion]

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
    )
    image_hash: models.TextField[str, str] = models.TextField(db_index=True)
    name: models.TextField[str, str] = models.TextField(default="")
    type_line: models.TextField[str, str] = models.TextField(default="")
    mana_cost: models.TextField[str, str] = models.TextField(default="")
    mana_symbols_json = models.JSONField(default=list)
    mana_value: models.IntegerField[int | None, int | None] = models.IntegerField(default=None, null=True, db_index=True)
    attack: models.IntegerField[int | None, int | None] = models.IntegerField(default=None, null=True)
    health: models.IntegerField[int | None, int | None] = models.IntegerField(default=None, null=True)
    rules_text_raw: models.TextField[str, str] = models.TextField(default="")
    rules_text_enriched: models.TextField[str, str] = models.TextField(default="")
    rules_text: models.TextField[str, str] = models.TextField(default="")
    confidence: models.FloatField[float, float] = models.FloatField(default=0.0)
    parse_result: models.ForeignKey[ParseResult | None, ParseResult | None] = models.ForeignKey(
        "ParseResult",
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="parse_result_id",
        default=None,
        null=True,
        db_index=True,
    )
    field_sources_json = models.JSONField(default=dict)
    parsed_snapshot_json = models.JSONField(default=dict)
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
    content_version: models.ForeignKey[ContentVersion | None, ContentVersion | None] = models.ForeignKey(
        "ContentVersion",
        on_delete=models.SET_NULL,
        related_name="card_versions",
        db_column="content_version_id",
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
        indexes = [
            models.Index(fields=["card_version", "-created_at"], name="ix_cv_image_version_created"),
        ]


class ParseResult(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version: models.ForeignKey[CardVersion, CardVersion] = models.ForeignKey(
        "CardVersion",
        on_delete=models.CASCADE,
        related_name="parse_results",
        db_column="card_version_id",
    )
    raw_ocr_json = models.JSONField(default=dict)
    normalized_fields_json = models.JSONField(default=dict)
    confidence_json = models.JSONField(default=dict)

    class Meta:
        db_table = "parse_result"


