from __future__ import annotations

from rest_framework import serializers

from card_reader_core.models import ImportJob, ImportJobItem


class ImportUploadSerializer(serializers.Serializer):
    template_id = serializers.CharField()
    options_json = serializers.CharField(default="{}")
    files = serializers.ListField(child=serializers.FileField(), allow_empty=False)


class ImportJobSerializer(serializers.Serializer):
    id = serializers.CharField()
    source_path = serializers.CharField()
    template_id = serializers.CharField()
    status = serializers.CharField()
    total_items = serializers.IntegerField()
    processed_items = serializers.IntegerField()


class ImportJobItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    source_file = serializers.CharField()
    status = serializers.CharField()
    error_message = serializers.CharField(allow_null=True, required=False)


class ImportJobDetailSerializer(ImportJobSerializer):
    items = ImportJobItemSerializer(many=True)


def import_job_payload(job: ImportJob) -> dict[str, object]:
    return ImportJobSerializer(job).data


def import_detail_payload(job: ImportJob, items: list[ImportJobItem]) -> dict[str, object]:
    return ImportJobDetailSerializer({**import_job_payload(job), "items": items}).data
