from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from django.db import models

from .base import TimestampedModel, uuid_str
from .card import CARD_POOL_CHOICES

if TYPE_CHECKING:
    from .card_version import CardVersion, ParseResult


class Tag(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    identifiers_json = models.JSONField(default=list)

    class Meta:
        db_table = "tag"


class Symbol(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    symbol_type: models.TextField[str, str] = models.TextField(default="generic", db_index=True)
    detector_type: models.TextField[str, str] = models.TextField(default="template", db_index=True)
    detection_config_json = models.JSONField(default=dict)
    text_enrichment_json = models.JSONField(default=dict)
    reference_assets_json = models.JSONField(default=list)
    text_token: models.TextField[str, str] = models.TextField(default="")
    enabled: models.BooleanField[bool, bool] = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "symbol"


class Keyword(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    identifiers_json = models.JSONField(default=list)

    class Meta:
        db_table = "keyword"


class Type(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")
    identifiers_json = models.JSONField(default=list)

    class Meta:
        db_table = "type"


CARD_CLASSIFICATION_TARGET_ROLE: Literal["role"] = "role"
CARD_CLASSIFICATION_TARGET_FACTION: Literal["faction"] = "faction"
CardClassificationTargetKind = Literal["role", "faction"]
CARD_CLASSIFICATION_TARGET_KIND_CHOICES = (
    (CARD_CLASSIFICATION_TARGET_ROLE, "Role"),
    (CARD_CLASSIFICATION_TARGET_FACTION, "Faction"),
)

CARD_CLASSIFICATION_SOURCE_TAG: Literal["tag"] = "tag"
CARD_CLASSIFICATION_SOURCE_TYPE: Literal["type"] = "type"
CardClassificationSourceKind = Literal["tag", "type"]
CARD_CLASSIFICATION_SOURCE_KIND_CHOICES = (
    (CARD_CLASSIFICATION_SOURCE_TAG, "Tag"),
    (CARD_CLASSIFICATION_SOURCE_TYPE, "Type"),
)


class CardClassificationRule(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_pool: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=CARD_POOL_CHOICES,
        db_index=True,
    )
    target_kind: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=CARD_CLASSIFICATION_TARGET_KIND_CHOICES,
        db_index=True,
    )
    target_key: models.CharField[str, str] = models.CharField(max_length=64, db_index=True)
    source_kind: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=CARD_CLASSIFICATION_SOURCE_KIND_CHOICES,
        db_index=True,
    )
    tag: models.ForeignKey[Tag | None, Tag | None] = models.ForeignKey(
        "Tag",
        on_delete=models.PROTECT,
        related_name="classification_rules",
        db_column="tag_id",
        null=True,
        blank=True,
        default=None,
    )
    type: models.ForeignKey[Type | None, Type | None] = models.ForeignKey(
        "Type",
        on_delete=models.PROTECT,
        related_name="classification_rules",
        db_column="type_id",
        null=True,
        blank=True,
        default=None,
    )
    enabled: models.BooleanField[bool, bool] = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "card_classification_rule"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        source_kind=CARD_CLASSIFICATION_SOURCE_TAG,
                        tag__isnull=False,
                        type__isnull=True,
                    )
                    | models.Q(
                        source_kind=CARD_CLASSIFICATION_SOURCE_TYPE,
                        tag__isnull=True,
                        type__isnull=False,
                    )
                ),
                name="ck_classification_rule_source_fk",
            ),
            models.UniqueConstraint(
                fields=("card_pool", "target_kind", "target_key", "tag"),
                condition=models.Q(source_kind=CARD_CLASSIFICATION_SOURCE_TAG),
                name="uq_class_rule_tag_target",
            ),
            models.UniqueConstraint(
                fields=("card_pool", "target_kind", "target_key", "type"),
                condition=models.Q(source_kind=CARD_CLASSIFICATION_SOURCE_TYPE),
                name="uq_class_rule_type_target",
            ),
        ]
        indexes = [
            models.Index(fields=("card_pool", "enabled", "tag"), name="ix_class_rule_pool_tag"),
            models.Index(fields=("card_pool", "enabled", "type"), name="ix_class_rule_pool_type"),
        ]


class MetadataSuggestion(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    kind: models.TextField[str, str] = models.TextField(default="", db_index=True)
    normalized_value: models.TextField[str, str] = models.TextField(default="", db_index=True)
    display_value: models.TextField[str, str] = models.TextField(default="")
    status: models.TextField[str, str] = models.TextField(default="pending", db_index=True)
    accepted_tag: models.ForeignKey[Tag | None, Tag | None] = models.ForeignKey(
        "Tag",
        on_delete=models.SET_NULL,
        related_name="accepted_metadata_suggestions",
        db_column="accepted_tag_id",
        default=None,
        null=True,
        blank=True,
    )
    accepted_type: models.ForeignKey[Type | None, Type | None] = models.ForeignKey(
        "Type",
        on_delete=models.SET_NULL,
        related_name="accepted_metadata_suggestions",
        db_column="accepted_type_id",
        default=None,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "metadata_suggestion"
        constraints = [
            models.UniqueConstraint(
                fields=("kind", "normalized_value"),
                name="ux_metadata_suggestion_kind_value",
            )
        ]


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
        indexes = [
            models.Index(fields=["tag", "card_version"], name="ix_cv_tag_tag_version"),
        ]
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
        indexes = [
            models.Index(fields=["symbol", "card_version"], name="ix_cv_symbol_symbol_version"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("card_version", "symbol"), name="ux_card_version_symbol_pair"
            )
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
        indexes = [
            models.Index(fields=["keyword", "card_version"], name="ix_cv_keyword_keyword_version"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("card_version", "keyword"), name="ux_card_version_keyword_pair"
            )
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
        indexes = [
            models.Index(fields=["type", "card_version"], name="ix_cv_type_type_version"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("card_version", "type"), name="ux_card_version_type_pair"
            )
        ]


class CardVersionMetadataSuggestion(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version: models.ForeignKey[CardVersion, CardVersion] = models.ForeignKey(
        "CardVersion",
        on_delete=models.CASCADE,
        related_name="card_version_metadata_suggestions",
        db_column="card_version_id",
    )
    suggestion: models.ForeignKey[MetadataSuggestion, MetadataSuggestion] = models.ForeignKey(
        "MetadataSuggestion",
        on_delete=models.CASCADE,
        related_name="card_version_metadata_suggestions",
        db_column="suggestion_id",
    )
    parse_result: models.ForeignKey[ParseResult | None, ParseResult | None] = models.ForeignKey(
        "ParseResult",
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="parse_result_id",
        default=None,
        null=True,
        blank=True,
    )
    source_text: models.TextField[str, str] = models.TextField(default="")
    normalized_source_text: models.TextField[str, str] = models.TextField(default="")

    class Meta:
        db_table = "card_version_metadata_suggestion"
        constraints = [
            models.UniqueConstraint(
                fields=("card_version", "suggestion"),
                name="ux_card_version_metadata_suggestion_pair",
            )
        ]
