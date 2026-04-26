from __future__ import annotations

from django.db import models

from .base import TimestampedModel, uuid_str


class Tag(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")

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

    class Meta:
        db_table = "keyword"


class Type(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    key: models.TextField[str, str] = models.TextField(default="", db_index=True, unique=True)
    label: models.TextField[str, str] = models.TextField(default="")

    class Meta:
        db_table = "type"


class CardVersionTag(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version_id: models.TextField[str, str] = models.TextField(db_index=True)
    tag_id: models.TextField[str, str] = models.TextField(db_index=True)

    class Meta:
        db_table = "card_version_tag"
        constraints = [
            models.UniqueConstraint(fields=("card_version_id", "tag_id"), name="ux_card_version_tag_pair")
        ]


class CardVersionSymbol(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version_id: models.TextField[str, str] = models.TextField(db_index=True)
    symbol_id: models.TextField[str, str] = models.TextField(db_index=True)

    class Meta:
        db_table = "card_version_symbol"
        constraints = [
            models.UniqueConstraint(fields=("card_version_id", "symbol_id"), name="ux_card_version_symbol_pair")
        ]


class CardVersionKeyword(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version_id: models.TextField[str, str] = models.TextField(db_index=True)
    keyword_id: models.TextField[str, str] = models.TextField(db_index=True)

    class Meta:
        db_table = "card_version_keyword"
        constraints = [
            models.UniqueConstraint(fields=("card_version_id", "keyword_id"), name="ux_card_version_keyword_pair")
        ]


class CardVersionType(TimestampedModel):
    id: models.TextField[str, str] = models.TextField(default=uuid_str, primary_key=True)
    card_version_id: models.TextField[str, str] = models.TextField(db_index=True)
    type_id: models.TextField[str, str] = models.TextField(db_index=True)

    class Meta:
        db_table = "card_version_type"
        constraints = [
            models.UniqueConstraint(fields=("card_version_id", "type_id"), name="ux_card_version_type_pair")
        ]


