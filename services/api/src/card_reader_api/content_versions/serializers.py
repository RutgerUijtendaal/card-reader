from __future__ import annotations

from rest_framework import serializers

from card_reader_core.models import CardVersion, ContentVersion
from card_reader_core.repositories.content_versions import normalize_description, parse_version_number


def content_version_payload(version: ContentVersion) -> dict[str, object]:
    annotated_card_count = getattr(version, "card_count", None)
    card_count = annotated_card_count if isinstance(annotated_card_count, int) else CardVersion.objects.filter(content_version_id=version.id).count()
    return {
        "id": version.id,
        "version_number": version.version_number,
        "base_version": version.base_version,
        "description": version.description,
        "card_count": card_count,
        "created_at": version.created_at.isoformat(),
        "updated_at": version.updated_at.isoformat(),
    }


class ContentVersionUpdateSerializer(serializers.Serializer[dict[str, object]]):
    version_number = serializers.CharField(required=False)
    description = serializers.CharField(required=False)

    def validate_version_number(self, value: str) -> str:
        normalized = value.strip()
        try:
            major, minor, patch = parse_version_number(normalized)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return f"{major}.{minor}.{patch}"

    def validate_description(self, value: str) -> str:
        try:
            return normalize_description(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
