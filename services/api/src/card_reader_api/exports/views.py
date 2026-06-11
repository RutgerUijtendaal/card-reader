from __future__ import annotations

from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.cards.query_params import card_filter_query_data
from card_reader_api.cards.serializers import CardFiltersQuerySerializer
from card_reader_api.common.auth_access import is_authenticated
from card_reader_api.common.responses import not_found, serializer_error
from card_reader_api.exports.tts import encode_tts_deck_export, get_tts_export_sideboard, tts_export_filename
from card_reader_core.repositories.exports import export_cards_csv
from card_reader_core.services.decks import DeckService


class ExportCsvView(APIView):
    def get(self, request: Request) -> HttpResponse:
        serializer = CardFiltersQuerySerializer(data=card_filter_query_data(request))
        if not serializer.is_valid():
            return serializer_error(serializer)
        filters = serializer.validated_filters()
        content = export_cards_csv(
            query=filters["query"],
            max_confidence=filters["max_confidence"],
            keyword_ids=filters["keyword_ids"],
            keyword_match=filters["keyword_match"],
            tag_ids=filters["tag_ids"],
            tag_match=filters["tag_match"],
            mana_symbol_ids=filters["mana_symbol_ids"],
            mana_symbol_exclude_ids=filters["mana_symbol_exclude_ids"],
            mana_symbol_match=filters["mana_symbol_match"],
            affinity_symbol_ids=filters["affinity_symbol_ids"],
            affinity_symbol_exclude_ids=filters["affinity_symbol_exclude_ids"],
            affinity_symbol_match=filters["affinity_symbol_match"],
            devotion_symbol_ids=filters["devotion_symbol_ids"],
            devotion_symbol_exclude_ids=filters["devotion_symbol_exclude_ids"],
            devotion_symbol_match=filters["devotion_symbol_match"],
            other_symbol_ids=filters["other_symbol_ids"],
            other_symbol_exclude_ids=filters["other_symbol_exclude_ids"],
            other_symbol_match=filters["other_symbol_match"],
            symbol_ids=filters["symbol_ids"],
            type_ids=filters["type_ids"],
            type_match=filters["type_match"],
            mana_cost_min=filters["mana_cost_min"],
            mana_cost_max=filters["mana_cost_max"],
            template_id=filters["template_id"],
            attack_min=filters["attack_min"],
            attack_max=filters["attack_max"],
            health_min=filters["health_min"],
            health_max=filters["health_max"],
            lifecycle_status=filters["lifecycle_status"],
            sort=filters["sort"],
        )
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=cards.csv"
        return response


class DeckTtsExportView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, deck_id: str) -> HttpResponse | Response:
        viewer_id = _user_id(request) if is_authenticated(request.user) else None
        deck = DeckService().get_deck_for_viewer(deck_id, viewer_id=viewer_id)
        if deck is None:
            return not_found("Deck not found")

        sideboard_id = request.query_params.get("sideboard_id")
        sideboard = get_tts_export_sideboard(deck, sideboard_id)
        if sideboard_id is not None and sideboard is None:
            return not_found("Sideboard not found")

        content = encode_tts_deck_export(deck, sideboard_id=sideboard_id)
        filename = tts_export_filename(deck.name, sideboard_name=sideboard.name if sideboard is not None else None)
        response = HttpResponse(content, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


def _user_id(request: Request) -> str:
    return str(getattr(request.user, "pk", ""))
