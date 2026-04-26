from __future__ import annotations

from rest_framework import serializers


class TemplateSerializer(serializers.Serializer):
    id = serializers.CharField()
    key = serializers.CharField()
    label = serializers.CharField()
    definition_json = serializers.CharField()


def template_payload(row: object) -> dict[str, object]:
    return TemplateSerializer(row).data
