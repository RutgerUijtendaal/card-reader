from __future__ import annotations

import json

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from card_reader_core.models import ContentVersion, ImportJob, ImportJobItem
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
            }
            for item in items
        ],
    }


class ImportUploadSerializer(serializers.Serializer[dict[str, object]]):
    template_id = serializers.CharField()
    content_version_base = serializers.CharField()
    content_version_description = serializers.CharField()
    options_json = serializers.CharField(required=False, default="{}")
    files = serializers.ListField(child=serializers.FileField(), allow_empty=False)

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
