from __future__ import annotations

import json

from rest_framework import serializers

from card_reader_core.models import CARD_ROLES, Template, normalize_card_roles


def template_payload(row: Template) -> dict[str, object]:
    return {
        "id": row.id,
        "key": row.key,
        "label": row.label,
        "definition_json": row.definition_json,
        "inferred_card_roles": list(normalize_card_roles(row.inferred_card_roles_json)),
    }


class TemplateWriteSerializer(serializers.Serializer[dict[str, object]]):
    label = serializers.CharField(required=True, allow_blank=False)  # type: ignore[assignment]
    key = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    definition_json = serializers.JSONField(required=True)
    inferred_card_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=CARD_ROLES),
        required=False,
        default=list,
    )

    def validate_definition_json(self, value: object) -> str:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError("definition_json must be valid JSON") from exc
        if not isinstance(value, dict):
            raise serializers.ValidationError("definition_json must be a JSON object")
        return json.dumps(value)

    def validate_inferred_card_roles(self, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Roles must be unique.")
        return list(normalize_card_roles(value))


class TemplateReparseSerializer(serializers.Serializer[dict[str, object]]):
    source_template_id = serializers.CharField(required=True, allow_blank=False)
