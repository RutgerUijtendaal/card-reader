from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from .base import TimestampedModel, uuid_str

if TYPE_CHECKING:
    from .card_version import CardVersion


class Tag(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    identifiers_json: models.TextField[str, str] = models.TextField(default="[]")

    class Meta:
        db_table = "tag"


class Symbol(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    symbol_type: models.TextField[str, str] = models.TextField(default="generic", db_index=True)
    detector_type: models.TextField[str, str] = models.TextField(default="template", db_index=True)
    detection_config_json: models.TextField[str, str] = models.TextField(default="{}")
    reference_assets_json: models.TextField[str, str] = models.TextField(default="[]")
    text_token: models.TextField[str, str] = models.TextField(default="")
    enabled: models.BooleanField[bool, bool] = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "symbol"


class Keyword(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    identifiers_json: models.TextField[str, str] = models.TextField(default="[]")

    class Meta:
        db_table = "keyword"


class Type(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    identifiers_json: models.TextField[str, str] = models.TextField(default="[]")

    class Meta:
        db_table = "type"


class CardVersionTag(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version: models.ForeignKey[CardVersion, CardVersion] = models.ForeignKey(
        "CardVersion",
        on_delete=models.CASCADE,
        related_name="card_version_tags",
        db_column="card_version_id",
    )
    tag: models.ForeignKey[Tag, Tag] = models.ForeignKey(
        "Tag", on_delete=models.CASCADE, related_name="card_version_tags", db_column="tag_id"
    )

    class Meta:
        db_table = "card_version_tag"
        constraints = [
            models.UniqueConstraint(fields=("card_version", "tag"), name="ux_card_version_tag_pair")
        ]


class CardVersionSymbol(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version: models.ForeignKey[CardVersion, CardVersion] = models.ForeignKey(
        "CardVersion",
        on_delete=models.CASCADE,
        related_name="card_version_symbols",
        db_column="card_version_id",
    )
    symbol: models.ForeignKey[Symbol, Symbol] = models.ForeignKey(
        "Symbol",
        on_delete=models.CASCADE,
        related_name="card_version_symbols",
        db_column="symbol_id",
    )

    class Meta:
        db_table = "card_version_symbol"
        constraints = [
            models.UniqueConstraint(fields=("card_version", "symbol"), name="ux_card_version_symbol_pair")
        ]


class CardVersionKeyword(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version: models.ForeignKey[CardVersion, CardVersion] = models.ForeignKey(
        "CardVersion",
        on_delete=models.CASCADE,
        related_name="card_version_keywords",
        db_column="card_version_id",
    )
    keyword: models.ForeignKey[Keyword, Keyword] = models.ForeignKey(
        "Keyword",
        on_delete=models.CASCADE,
        related_name="card_version_keywords",
        db_column="keyword_id",
    )

    class Meta:
        db_table = "card_version_keyword"
        constraints = [
            models.UniqueConstraint(fields=("card_version", "keyword"), name="ux_card_version_keyword_pair")
        ]


class CardVersionType(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version: models.ForeignKey[CardVersion, CardVersion] = models.ForeignKey(
        "CardVersion",
        on_delete=models.CASCADE,
        related_name="card_version_types",
        db_column="card_version_id",
    )
    type: models.ForeignKey[Type, Type] = models.ForeignKey(
        "Type", on_delete=models.CASCADE, related_name="card_version_types", db_column="type_id"
    )

    class Meta:
        db_table = "card_version_type"
        constraints = [
            models.UniqueConstraint(fields=("card_version", "type"), name="ux_card_version_type_pair")
        ]


