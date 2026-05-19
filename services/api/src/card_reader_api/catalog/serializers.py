from __future__ import annotations

import json

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from card_reader_core.models import Keyword, Symbol, Tag, Type
from card_reader_core.services.catalog import (
    CatalogSuggestionDetail,
    KeywordDetail,
    LinkedCardPreview,
    SuggestionOccurrencePreview,
    SymbolDetail,
    TagDetail,
    TypeDetail,
)


CatalogOption = Keyword | Tag | Type


def _catalog_option_payload(row: CatalogOption) -> dict[str, object]:
    return {
        "id": row.id,
        "key": row.key,
        "label": row.label,
    }


def keyword_payload(row: Keyword) -> dict[str, object]:
    payload = _catalog_option_payload(row)
    payload["identifiers"] = row.identifiers_json
    payload["linked_card_count"] = int(getattr(row, "linked_card_count", 0))
    return payload


def tag_payload(row: Tag) -> dict[str, object]:
    payload = _catalog_option_payload(row)
    payload["identifiers"] = row.identifiers_json
    payload["linked_card_count"] = int(getattr(row, "linked_card_count", 0))
    return payload


def type_payload(row: Type) -> dict[str, object]:
    payload = _catalog_option_payload(row)
    payload["identifiers"] = row.identifiers_json
    payload["linked_card_count"] = int(getattr(row, "linked_card_count", 0))
    return payload


def symbol_payload(row: Symbol) -> dict[str, object]:
    return {
        "id": row.id,
        "key": row.key,
        "label": row.label,
        "symbol_type": row.symbol_type,
        "detector_type": row.detector_type,
        "detection_config_json": row.detection_config_json,
        "text_enrichment_json": row.text_enrichment_json,
        "reference_assets_json": row.reference_assets_json,
        "text_token": row.text_token,
        "enabled": row.enabled,
        "linked_card_count": int(getattr(row, "linked_card_count", 0)),
    }


def suggestion_occurrence_payload(row: SuggestionOccurrencePreview) -> dict[str, object]:
    return {
        "card_id": row["card_id"],
        "card_label": row["card_label"],
        "card_version_id": row["card_version_id"],
        "card_version_name": row["card_version_name"],
        "image_url": row["image_url"],
        "source_text": row["source_text"],
        "normalized_source_text": row["normalized_source_text"],
    }


def linked_card_payload(row: LinkedCardPreview) -> dict[str, object]:
    return {
        "card_id": row["card_id"],
        "card_label": row["card_label"],
        "card_version_id": row["card_version_id"],
        "card_version_name": row["card_version_name"],
        "image_url": row["image_url"],
    }


def suggestion_payload(row: CatalogSuggestionDetail) -> dict[str, object]:
    accepted_target = None
    if row["accepted_tag"] is not None:
        accepted_target = tag_payload(row["accepted_tag"])
    elif row["accepted_type"] is not None:
        accepted_target = type_payload(row["accepted_type"])

    return {
        "id": row["id"],
        "kind": row["kind"],
        "display_value": row["display_value"],
        "normalized_value": row["normalized_value"],
        "status": row["status"],
        "occurrence_count": row["occurrence_count"],
        "accepted_target": accepted_target,
        "occurrences": [suggestion_occurrence_payload(item) for item in row["occurrences"]],
    }


def keyword_detail_payload(row: KeywordDetail) -> dict[str, object]:
    payload = keyword_payload(row["entry"])
    payload["linked_cards"] = [linked_card_payload(item) for item in row["linked_cards"]]
    payload["linked_card_count"] = row["linked_card_count"]
    return payload


def tag_detail_payload(row: TagDetail) -> dict[str, object]:
    payload = tag_payload(row["entry"])
    payload["linked_cards"] = [linked_card_payload(item) for item in row["linked_cards"]]
    payload["linked_card_count"] = row["linked_card_count"]
    return payload


def type_detail_payload(row: TypeDetail) -> dict[str, object]:
    payload = type_payload(row["entry"])
    payload["linked_cards"] = [linked_card_payload(item) for item in row["linked_cards"]]
    payload["linked_card_count"] = row["linked_card_count"]
    return payload


def symbol_detail_payload(row: SymbolDetail) -> dict[str, object]:
    payload = symbol_payload(row["entry"])
    payload["linked_cards"] = [linked_card_payload(item) for item in row["linked_cards"]]
    payload["linked_card_count"] = row["linked_card_count"]
    return payload


class CatalogEntryWriteSerializer(serializers.Serializer[dict[str, object]]):
    label = serializers.CharField(required=True, allow_blank=False)  # type: ignore[assignment]
    key = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    identifiers = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )


class SymbolWriteSerializer(serializers.Serializer[dict[str, object]]):
    label = serializers.CharField(required=True, allow_blank=False)  # type: ignore[assignment]
    key = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    symbol_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    detector_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    detection_config_json = serializers.JSONField(required=False)
    text_enrichment_json = serializers.JSONField(required=False)
    reference_assets_json = serializers.JSONField(required=False)
    text_token = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    enabled = serializers.BooleanField(required=False, allow_null=True)

    def validate_detection_config_json(self, value: object) -> str:
        if not isinstance(value, dict):
            raise serializers.ValidationError("detection_config_json must be a JSON object")
        return json.dumps(value)

    def validate_reference_assets_json(self, value: object) -> str:
        if not isinstance(value, list):
            raise serializers.ValidationError("reference_assets_json must be a JSON array")
        if not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError("reference_assets_json entries must be strings")
        return json.dumps(value)

    def validate_text_enrichment_json(self, value: object) -> str:
        if not isinstance(value, dict):
            raise serializers.ValidationError("text_enrichment_json must be a JSON object")
        return json.dumps(value)


class SymbolAssetUploadSerializer(serializers.Serializer[dict[str, object]]):
    file = serializers.FileField()

    def validate_file(self, value: UploadedFile) -> UploadedFile:
        if not value.name:
            raise serializers.ValidationError("file is required")
        return value


class SuggestionAcceptSerializer(serializers.Serializer[dict[str, object]]):
    target_id = serializers.CharField(required=False, allow_blank=False)
    label = serializers.CharField(required=False, allow_blank=False, allow_null=True)  # type: ignore[assignment]
    key = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SuggestionStatusQuerySerializer(serializers.Serializer[dict[str, object]]):
    status = serializers.ChoiceField(
        choices=["pending", "accepted", "rejected"],
        required=False,
        allow_null=True,
    )
