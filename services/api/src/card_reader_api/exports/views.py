from __future__ import annotations

from django.http import HttpResponse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from card_reader_api.cards.serializers import CardFiltersQuerySerializer
from card_reader_core.repositories.exports_repository import export_cards_csv


class ExportCsvView(APIView):
    def get(self, request: Request) -> HttpResponse:
        serializer = CardFiltersQuerySerializer(data=_query_data(request))
        if not serializer.is_valid():
            return _serializer_error(serializer)
        filters = serializer.validated_filters()
        content = export_cards_csv(
            query=filters["query"],
            max_confidence=filters["max_confidence"],
            keyword_ids=filters["keyword_ids"],
            tag_ids=filters["tag_ids"],
            symbol_ids=filters["symbol_ids"],
            type_ids=filters["type_ids"],
            mana_cost=filters["mana_cost"],
            template_id=filters["template_id"],
            attack_min=filters["attack_min"],
            attack_max=filters["attack_max"],
            health_min=filters["health_min"],
            health_max=filters["health_max"],
        )
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=cards.csv"
        return response


def _query_data(request: Request) -> dict[str, object]:
    return {
        "query": request.query_params.get("q"),
        "max_confidence": request.query_params.get("max_confidence"),
        "keyword_ids": request.query_params.getlist("keyword_ids"),
        "tag_ids": request.query_params.getlist("tag_ids"),
        "symbol_ids": request.query_params.getlist("symbol_ids"),
        "type_ids": request.query_params.getlist("type_ids"),
        "mana_cost": request.query_params.get("mana_cost"),
        "template_id": request.query_params.get("template_id"),
        "attack_min": request.query_params.get("attack_min"),
        "attack_max": request.query_params.get("attack_max"),
        "health_min": request.query_params.get("health_min"),
        "health_max": request.query_params.get("health_max"),
    }


def _serializer_error(serializer: Serializer[object]) -> Response:
    detail = next(iter(serializer.errors.values()))
    if isinstance(detail, list):
        detail = detail[0]
    return Response({"detail": str(detail)}, status=status.HTTP_400_BAD_REQUEST)
