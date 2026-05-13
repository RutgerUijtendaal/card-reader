from __future__ import annotations

import json

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from card_reader_core.models import ImportJob, ImportJobItem


def import_job_payload(job: ImportJob) -> dict[str, object]:
    return {
        "id": job.id,
        "source_path": job.source_path,
        "template_id": job.template_id,
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
            }
            for item in items
        ],
    }


class ImportUploadSerializer(serializers.Serializer[dict[str, object]]):
    template_id = serializers.CharField()
    options_json = serializers.CharField(required=False, default="{}")
    files = serializers.ListField(child=serializers.FileField(), allow_empty=False)

    def validate_files(self, value: list[UploadedFile]) -> list[UploadedFile]:
        if not value:
            raise serializers.ValidationError("At least one file is required")
        return value

    def validate_options_json(self, value: str) -> dict[str, object]:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError("options_json must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise serializers.ValidationError("options_json must decode to an object")
        return payload
