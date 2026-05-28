from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from card_reader_api.templates.serializers import TemplateReparseSerializer, TemplateWriteSerializer, template_payload
from card_reader_core.repositories.cards import list_latest_card_version_reparse_sources
from card_reader_core.repositories.import_jobs import ImportJobItemTarget, create_import_job_with_files
from card_reader_core.config.settings import settings
from card_reader_core.services.templates import TemplateService


class TemplateListCreateView(APIView):
    def get(self, _request: Request) -> Response:
        return Response([template_payload(row) for row in TemplateService().list_templates()])

    def post(self, request: Request) -> Response:
        serializer = TemplateWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        try:
            row = TemplateService().create_template(
                label=serializer.validated_data["label"],
                key=serializer.validated_data.get("key"),
                definition_json=serializer.validated_data["definition_json"],
            )
        except ValueError as exc:
            return _bad_request(str(exc))
        return Response(template_payload(row))


class TemplateDetailView(APIView):
    def patch(self, request: Request, entry_id: str) -> Response:
        serializer = TemplateWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return _serializer_error(serializer)
        try:
            row = TemplateService().update_template(
                entry_id=entry_id,
                label=serializer.validated_data.get("label"),
                key=serializer.validated_data.get("key"),
                definition_json=serializer.validated_data.get("definition_json"),
            )
        except ValueError as exc:
            return _bad_request(str(exc))
        if row is None:
            return _not_found("Template not found")
        return Response(template_payload(row))

    def delete(self, _request: Request, entry_id: str) -> Response:
        if not TemplateService().delete_template(entry_id=entry_id):
            return _not_found("Template not found")
        return Response(status=status.HTTP_204_NO_CONTENT)


class TemplateReparseView(APIView):
    def post(self, request: Request, entry_id: str) -> Response:
        serializer = TemplateReparseSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_error(serializer)

        target_template = TemplateService().get_template(entry_id)
        if target_template is None:
            return _not_found("Template not found")

        source_template_id = serializer.validated_data["source_template_id"]
        if TemplateService().get_template_by_key(source_template_id) is None:
            return _bad_request(f"Unknown source_template_id '{source_template_id}'")

        matching_sources = [
            source
            for source in list_latest_card_version_reparse_sources()
            if source.template_id == source_template_id
        ]
        if not matching_sources:
            return Response({"message": "No latest card versions found for the selected source template."})

        create_import_job_with_files(
            source_path=settings.storage_root_dir / "templates" / f"reparse-{target_template.key}",
            template_id=target_template.key,
            options={"reparse_existing": True},
            files=[source.image_path for source in matching_sources],
            item_targets=[
                ImportJobItemTarget(card_id=source.card_id, card_version_id=source.card_version_id)
                for source in matching_sources
            ],
        )
        return Response(
            {
                "message": (
                    f"Queued reparse for {len(matching_sources)} latest card "
                    f"image{'s' if len(matching_sources) != 1 else ''} into template '{target_template.key}'."
                )
            },
            status=status.HTTP_202_ACCEPTED,
        )


def _bad_request(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _not_found(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_404_NOT_FOUND)


def _serializer_error(serializer: BaseSerializer[Any]) -> Response:
    errors = serializer.errors
    detail = next(iter(cast(Mapping[str, object], errors).values()), "Invalid request.")
    if isinstance(detail, list):
        detail = detail[0]
    return Response({"detail": str(detail)}, status=status.HTTP_400_BAD_REQUEST)
