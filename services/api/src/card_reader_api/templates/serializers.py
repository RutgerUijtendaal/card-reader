from __future__ import annotations

import json

from rest_framework import serializers

from card_reader_core.models import Template


def template_payload(row: Template) -> dict[str, object]:
    return {
        "id": row.id,
        "key": row.key,
        "label": row.label,
        "definition_json": row.definition_json,
    }


class TemplateWriteSerializer(serializers.Serializer[dict[str, object]]):
    label = serializers.CharField(required=True, allow_blank=False)
    key = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    definition_json = serializers.JSONField(required=True)

    def validate_definition_json(self, value: object) -> str:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError("definition_json must be valid JSON") from exc
        if not isinstance(value, dict):
            raise serializers.ValidationError("definition_json must be a JSON object")
        return json.dumps(value)
