from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.templates.serializers import template_payload
from card_reader_core.services.templates import TemplateService


class TemplateListCreateView(APIView):
    def get(self, _request: Request) -> Response:
        return Response([template_payload(row) for row in TemplateService().list_templates()])

    def post(self, request: Request) -> Response:
        label = request.data.get("label")
        definition_json = request.data.get("definition_json")
        if label is None:
            return _bad_request("label is required")
        if definition_json is None:
            return _bad_request("definition_json is required")
        try:
            row = TemplateService().create_template(
                label=str(label),
                key=request.data.get("key"),
                definition_json=str(definition_json),
            )
        except ValueError as exc:
            return _bad_request(str(exc))
        return Response(template_payload(row))


class TemplateDetailView(APIView):
    def patch(self, request: Request, entry_id: str) -> Response:
        try:
            row = TemplateService().update_template(
                entry_id=entry_id,
                label=request.data.get("label"),
                key=request.data.get("key"),
                definition_json=request.data.get("definition_json"),
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
