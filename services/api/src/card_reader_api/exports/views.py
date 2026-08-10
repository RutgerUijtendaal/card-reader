from __future__ import annotations

from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.cards.query_params import card_filter_query_data
from card_reader_api.cards.serializers import CardFiltersQuerySerializer
from card_reader_api.common.auth_access import card_pool_scope_for_user, is_authenticated
from card_reader_api.common.permissions import StaffAllowed
from card_reader_api.common.responses import not_found, serializer_error
from card_reader_api.common.urls import build_public_api_url
from card_reader_api.exports.serializers import TtsCardExportRequestSerializer
from card_reader_api.exports.tts_cards import encode_tts_card_export
from card_reader_core.repositories.exports import export_cards_csv
from card_reader_core.services.decks import DeckService, deck_export_uses_out_of_scope_card
from card_reader_core.services.exports import (
    TtsCardExportError,
    TtsCardExportErrorCode,
    TtsCardExportService,
)
from card_reader_core.models import PLAYER_CARD_POOL_SCOPE

_TTS_CARD_EXPORT_ERROR_STATUS = {
    TtsCardExportErrorCode.CARD_BACK_UNAVAILABLE: 409,
    TtsCardExportErrorCode.CONTENT_VERSION_NOT_FOUND: 404,
    TtsCardExportErrorCode.DECK_SOURCE_NOT_FOUND: 404,
    TtsCardExportErrorCode.NO_USABLE_CARDS: 400,
    TtsCardExportErrorCode.REQUIRED_CARD_UNAVAILABLE: 409,
    TtsCardExportErrorCode.SHEETS_UNAVAILABLE: 503,
}
_RETRYABLE_TTS_CARD_EXPORT_ERRORS = {
    TtsCardExportErrorCode.SHEETS_UNAVAILABLE,
}


class ExportCsvView(APIView):
    def get(self, request: Request) -> HttpResponse | Response:
        card_pool_scope = card_pool_scope_for_user(request.user)
        serializer = CardFiltersQuerySerializer(data=card_filter_query_data(request))
        if not serializer.is_valid():
            return serializer_error(serializer)
        filters = serializer.validated_filters()
        if not card_pool_scope.allows_card_pool(filters["card_pool"]):
            return Response({"detail": "Game Master cards require staff access."}, status=status.HTTP_403_FORBIDDEN)
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
            mana_family_keys=filters["mana_family_keys"],
            mana_family_exclude_keys=filters["mana_family_exclude_keys"],
            mana_family_match=filters["mana_family_match"],
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
            card_pool=filters["card_pool"],
            card_roles=filters["card_roles"],
            card_role_exclude=filters["card_role_exclude"],
            card_role_match=filters["card_role_match"],
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
        if deck_export_uses_out_of_scope_card(
            deck,
            PLAYER_CARD_POOL_SCOPE,
            sideboard_id=sideboard_id,
        ):
            return not_found("Deck not found")
        try:
            export_data = TtsCardExportService().build_deck_export(
                str(deck.id),
                sideboard_id=sideboard_id,
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


def _user_id(request: Request) -> str:
    return str(getattr(request.user, "pk", ""))


def _tts_card_export_error_response(exc: TtsCardExportError) -> Response:
    response = Response(
        {"detail": exc.detail},
        status=_TTS_CARD_EXPORT_ERROR_STATUS[exc.code],
    )
    if exc.code in _RETRYABLE_TTS_CARD_EXPORT_ERRORS:
        response["Retry-After"] = "2"
    return response
