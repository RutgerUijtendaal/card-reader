from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from card_reader_api.templates.serializers import TemplateWriteSerializer, template_payload
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


def _bad_request(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _not_found(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_404_NOT_FOUND)


def _serializer_error(serializer: Serializer[object]) -> Response:
    detail = next(iter(serializer.errors.values()))
    if isinstance(detail, list):
        detail = detail[0]
    return Response({"detail": str(detail)}, status=status.HTTP_400_BAD_REQUEST)
