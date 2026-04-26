from __future__ import annotations

from django.http import HttpResponse
from rest_framework.request import Request
from rest_framework.views import APIView

from card_reader_core.services import ExportService


class ExportCsvView(APIView):
    def get(self, request: Request) -> HttpResponse:
        content = ExportService().export_cards_csv(**_export_filters(request))
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=cards.csv"
        return response


def _export_filters(request: Request) -> dict[str, object]:
    return {
        "query": request.query_params.get("q"),
        "max_confidence": _float_param(request, "max_confidence"),
        "keyword_ids": request.query_params.getlist("keyword_ids") or None,
        "tag_ids": request.query_params.getlist("tag_ids") or None,
        "symbol_ids": request.query_params.getlist("symbol_ids") or None,
        "type_ids": request.query_params.getlist("type_ids") or None,
        "mana_cost": request.query_params.get("mana_cost"),
        "template_id": request.query_params.get("template_id"),
        "attack_min": _int_param(request, "attack_min"),
        "attack_max": _int_param(request, "attack_max"),
        "health_min": _int_param(request, "health_min"),
        "health_max": _int_param(request, "health_max"),
    }


def _float_param(request: Request, name: str) -> float | None:
    value = request.query_params.get(name)
    if value is None or value == "":
        return None
    return float(value)


def _int_param(request: Request, name: str) -> int | None:
    value = request.query_params.get(name)
    if value is None or value == "":
        return None
    return int(value)
