from __future__ import annotations

import json

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from card_reader_core.models import ContentVersion, ImportJob, ImportJobItem
from card_reader_core.models import CARD_FACTIONS, CARD_POOLS, CARD_ROLES
from card_reader_core.repositories.content_versions import parse_base_version


def content_version_payload(version: ContentVersion | None) -> dict[str, object] | None:
    if version is None:
        return None
    return {
        "id": version.id,
        "version_number": version.version_number,
        "base_version": version.base_version,
        "description": version.description,
    }


def import_job_payload(job: ImportJob) -> dict[str, object]:
    return {
        "id": job.id,
        "source_path": job.source_path,
        "template_id": job.template.key,
        "content_version": content_version_payload(job.content_version),
        "status": job.status,
        "total_items": job.total_items,
        "processed_items": job.processed_items,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "card_pool": job.card_pool,
        "card_role_mode": job.card_role_mode,
        "card_role_override": list(job.card_role_override_json),
        "card_faction_mode": job.card_faction_mode,
        "card_faction_override": list(job.card_faction_override_json),
        "classification_rule_snapshot": job.classification_rule_snapshot_json,
    }


def import_detail_payload(job: ImportJob, items: list[ImportJobItem]) -> dict[str, object]:
    return {
        **import_job_payload(job),
        "items": [
            {
                "id": item.id,
                "source_file": item.source_file,
                "status": item.status,
                "error_message": item.error_message,
                "warning_code": item.warning_code,
                "warning_message": item.warning_message,
                "warnings": item.warnings_json,
                "resolved_card_roles": item.resolved_card_roles_json,
                "resolved_card_factions": item.resolved_card_factions_json,
                "classification_inference": item.classification_inference_json,
                "target_card_id": item.target_card.id if item.target_card is not None else None,
                "target_card_version_id": (
                    item.target_card_version.id if item.target_card_version is not None else None
                ),
                "target_card_pool_snapshot": item.target_card_pool_snapshot,
                "target_card_roles_snapshot": item.target_card_roles_snapshot_json,
                "target_card_factions_snapshot": item.target_card_factions_snapshot_json,
                "card_tab_url": (
                    f"/cards/{item.target_card.id}/edit?tab=card"
                    if item.target_card is not None
                    else None
                ),
            }
            for item in items
        ],
    }


class ImportUploadSerializer(serializers.Serializer[dict[str, object]]):
    creation_key = serializers.UUIDField()
    template_id = serializers.CharField()
    content_version_base = serializers.CharField()
    content_version_description = serializers.CharField()
    options_json = serializers.CharField(required=False, default="{}")
    files = serializers.ListField(child=serializers.FileField(), allow_empty=False)
    card_pool = serializers.ChoiceField(choices=CARD_POOLS)
    card_role_mode = serializers.ChoiceField(
        choices=("automatic", "override"),
        required=False,
        default="automatic",
    )
    card_role_override = serializers.CharField(required=False, default="[]")
    card_faction_mode = serializers.ChoiceField(
        choices=("automatic", "override"),
        required=False,
        default="automatic",
    )
    card_faction_override = serializers.CharField(required=False, default="[]")

    def validate_files(self, value: list[UploadedFile]) -> list[UploadedFile]:
        if not value:
            raise serializers.ValidationError("At least one file is required")
        return value

    def validate_content_version_base(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError("Version is required.")
        try:
            parse_base_version(normalized)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return normalized

    def validate_content_version_description(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError("Version description is required.")
        return normalized

    def validate_options_json(self, value: str) -> dict[str, object]:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError("options_json must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise serializers.ValidationError("options_json must decode to an object")
        return payload

    def validate_card_role_override(self, value: str) -> list[str]:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError("card_role_override must be valid JSON") from exc
        if not isinstance(payload, list):
            raise serializers.ValidationError("card_role_override must decode to an array")
        if len(payload) != len(set(map(str, payload))):
            raise serializers.ValidationError("card_role_override roles must be unique")
        invalid = sorted({str(role) for role in payload if role not in CARD_ROLES})
        if invalid:
            raise serializers.ValidationError(f"Unsupported card roles: {', '.join(invalid)}")
        return [role for role in CARD_ROLES if role in payload]

    def validate_card_faction_override(self, value: str) -> list[str]:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError("card_faction_override must be valid JSON") from exc
        if not isinstance(payload, list):
            raise serializers.ValidationError("card_faction_override must decode to an array")
        if len(payload) != len(set(map(str, payload))):
            raise serializers.ValidationError("card_faction_override factions must be unique")
        invalid = sorted({str(faction) for faction in payload if faction not in CARD_FACTIONS})
        if invalid:
            raise serializers.ValidationError(f"Unsupported card factions: {', '.join(invalid)}")
        return [faction for faction in CARD_FACTIONS if faction in payload]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if attrs.get("card_role_mode") == "automatic" and attrs.get("card_role_override"):
            raise serializers.ValidationError(
                {"card_role_override": "Automatic role inference cannot include overrides."}
            )
        if attrs.get("card_faction_mode") == "automatic" and attrs.get("card_faction_override"):
            raise serializers.ValidationError(
                {"card_faction_override": ("Automatic faction inference cannot include overrides.")}
            )
        return attrs
