from __future__ import annotations

import json

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from card_reader_core.models import Keyword, Symbol, Tag, Type


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
    return payload


def tag_payload(row: Tag) -> dict[str, object]:
    payload = _catalog_option_payload(row)
    payload["identifiers"] = row.identifiers_json
    return payload


def type_payload(row: Type) -> dict[str, object]:
    payload = _catalog_option_payload(row)
    payload["identifiers"] = row.identifiers_json
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
    }


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
