from __future__ import annotations

from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.cards.query_params import card_filter_query_data
from card_reader_api.cards.serializers import CardFiltersQuerySerializer
from card_reader_api.common.auth_access import is_authenticated
from card_reader_api.common.permissions import StaffAllowed
from card_reader_api.common.responses import not_found, serializer_error
from card_reader_api.common.urls import build_public_api_url
from card_reader_api.exports.serializers import TtsCardExportRequestSerializer
from card_reader_api.exports.tts_cards import encode_tts_card_export
from card_reader_core.models import Deck, DeckSideboard
from card_reader_core.repositories.exports import export_cards_csv
from card_reader_core.services.decks import DeckService
from card_reader_core.services.exports import (
    TtsCardExportError,
    TtsCardExportErrorCode,
    TtsCardExportService,
)

_TTS_CARD_EXPORT_ERROR_STATUS = {
    TtsCardExportErrorCode.CARD_BACK_UNAVAILABLE: 409,
    TtsCardExportErrorCode.CONTENT_VERSION_NOT_FOUND: 404,
    TtsCardExportErrorCode.NO_USABLE_CARDS: 400,
    TtsCardExportErrorCode.REQUIRED_CARD_UNAVAILABLE: 409,
    TtsCardExportErrorCode.SHEETS_UNAVAILABLE: 503,
}
_RETRYABLE_TTS_CARD_EXPORT_ERRORS = {
    TtsCardExportErrorCode.SHEETS_UNAVAILABLE,
}


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
            type_exclude_ids=filters["type_exclude_ids"],
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


class CardTtsExportView(APIView):
    permission_classes = [StaffAllowed]

    def post(self, request: Request) -> HttpResponse | Response:
        serializer = TtsCardExportRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        source = serializer.validated_source()

        gallery_filters = None
        if source["type"] == "gallery":
            filters_serializer = CardFiltersQuerySerializer(data=source["filters"])
            if not filters_serializer.is_valid():
                return serializer_error(filters_serializer)
            gallery_filters = filters_serializer.validated_filters()

        service = TtsCardExportService()
        try:
            if source["type"] == "gallery":
                assert gallery_filters is not None
                export_data = service.build_gallery_export(gallery_filters)
            else:
                export_data = service.build_content_version_export(
                    str(source["content_version_id"])
                )
        except TtsCardExportError as exc:
            return _tts_card_export_error_response(exc)

        export = encode_tts_card_export(
            export_data,
            absolute_url=lambda path: build_public_api_url(request, path),
        )
        return Response(
            {
                "encoded_payload": export.encoded_payload,
                "exported_count": export.exported_count,
                "skipped_count": export.skipped_count,
                "sheet_count": export.sheet_count,
            }
        )


class DeckTtsExportView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, deck_id: str) -> HttpResponse | Response:
        viewer_id = _user_id(request) if is_authenticated(request.user) else None
        deck = DeckService().get_deck_for_viewer(deck_id, viewer_id=viewer_id)
        if deck is None:
            return not_found("Deck not found")

        sideboard_id = request.query_params.get("sideboard_id")
        sideboard = _get_tts_export_sideboard(deck, sideboard_id)
        if sideboard_id is not None and sideboard is None:
            return not_found("Sideboard not found")

        try:
            export_data = TtsCardExportService().build_deck_export(deck, sideboard=sideboard)
        except TtsCardExportError as exc:
            return _tts_card_export_error_response(exc)

        export = encode_tts_card_export(
            export_data,
            absolute_url=lambda path: build_public_api_url(request, path),
        )
        return Response(
            {
                "encoded_payload": export.encoded_payload,
                "exported_count": export.exported_count,
                "skipped_count": export.skipped_count,
                "sheet_count": export.sheet_count,
            }
        )


def _user_id(request: Request) -> str:
    return str(getattr(request.user, "pk", ""))


def _get_tts_export_sideboard(
    deck: Deck,
    sideboard_id: str | None,
) -> DeckSideboard | None:
    if sideboard_id is None:
        return None
    return next(
        (sideboard for sideboard in deck.sideboards.all() if str(sideboard.id) == sideboard_id),
        None,
    )


def _tts_card_export_error_response(exc: TtsCardExportError) -> Response:
    response = Response(
        {"detail": exc.detail},
        status=_TTS_CARD_EXPORT_ERROR_STATUS[exc.code],
    )
    if exc.code in _RETRYABLE_TTS_CARD_EXPORT_ERRORS:
        response["Retry-After"] = "2"
    return response
