from __future__ import annotations

from rest_framework import serializers


class KeywordSerializer(serializers.Serializer):
    id = serializers.CharField()
    key = serializers.CharField()
    label = serializers.CharField()


class TagSerializer(KeywordSerializer):
    pass


class TypeSerializer(KeywordSerializer):
    pass


class SymbolSerializer(serializers.Serializer):
    id = serializers.CharField()
    key = serializers.CharField()
    label = serializers.CharField()
    symbol_type = serializers.CharField()
    detector_type = serializers.CharField()
    detection_config_json = serializers.CharField()
    reference_assets_json = serializers.CharField()
    text_token = serializers.CharField(allow_blank=True)
    enabled = serializers.BooleanField()


def keyword_payload(row: object) -> dict[str, object]:
    return KeywordSerializer(row).data


def tag_payload(row: object) -> dict[str, object]:
    return TagSerializer(row).data


def type_payload(row: object) -> dict[str, object]:
    return TypeSerializer(row).data


def symbol_payload(row: object) -> dict[str, object]:
    return SymbolSerializer(row).data
