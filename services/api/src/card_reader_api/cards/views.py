from __future__ import annotations

from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.cards.file_views import file_response, immutable_card_image_response, symbol_asset_response
from card_reader_api.cards.grouped_gallery import grouped_gallery_payload
from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.cards.query_params import card_filter_query_data
from card_reader_api.cards.serializers import (
    CardFiltersQuerySerializer,
    CardVersionParseFlagCreateSerializer,
    LatestCardReparseSerializer,
    LatestVersionUpdateSerializer,
    card_deck_reference_payload,
    card_group_summary_payload,
    card_payload,
    metadata_option,
    symbol_option,
)
from card_reader_api.common.auth_access import is_authenticated
from card_reader_api.common.responses import serializer_error
from card_reader_api.decks.serializers import deck_payload
from card_reader_api.cards.services import CardActionService, CardReparseError
from card_reader_core.repositories.cards import (
    get_card,
    get_card_image,
    list_card_generations,
    list_cards,
    promote_card_version,
    update_latest_card_version,
)
from card_reader_core.repositories.parse_flags import ParseFlagItemInput
from card_reader_core.services.card_groups import CardGroupService
from card_reader_core.services.cards import (
    get_card_version_edit_state,
    get_card_version_metadata,
    get_card_with_image,
    get_filter_metadata,
    resolve_card_image_path,
)
from card_reader_core.services.decks import DeckService
from card_reader_core.services.parse_flags import create_parse_flag_for_card_version

CARD_DETAIL_DECK_REFERENCE_LIMIT = 3


class CardListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        serializer = CardFiltersQuerySerializer(data=card_filter_query_data(request, include_list_controls=True))
        if not serializer.is_valid():
            return serializer_error(serializer)
        filters = serializer.validated_list_filters()
        show_groups = filters["show_groups"]
        if show_groups:
            return Response(grouped_gallery_payload(filters))
        cards = list_cards(
            query=filters["query"],
            card_ids=filters["card_ids"],
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
            is_hero=filters["is_hero"],
            attack_min=filters["attack_min"],
            attack_max=filters["attack_max"],
            health_min=filters["health_min"],
            health_max=filters["health_max"],
            lifecycle_status=filters["lifecycle_status"],
            sort=filters["sort"],
            page=filters["page"],
            page_size=filters["page_size"],
        )
        payloads = []
        for row in cards.results:
            payloads.append(
                card_payload(
                    row.version.card,
                    row.version,
                    image_url=card_image_asset_url(row.image, fallback_url=f"/cards/{row.version.card.id}/image"),
                    metadata={
                        "keywords": row.keywords,
                        "tags": row.tags,
                        "symbols": row.symbols,
                        "types": row.types,
                    },
                )
            )
        return Response(
            {
                "count": cards.count,
                "next_page": cards.page + 1 if cards.page * cards.page_size < cards.count else None,
                "previous_page": cards.page - 1 if cards.page > 1 else None,
                "page": cards.page,
                "page_size": cards.page_size,
                "results": payloads,
            }
        )


class CardFiltersView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        metadata = get_filter_metadata()
        return Response(
            {
                "keywords": [metadata_option(row) for row in metadata["keywords"]],
                "tags": [metadata_option(row) for row in metadata["tags"]],
                "symbols": [symbol_option(row) for row in metadata["symbols"]],
                "types": [metadata_option(row) for row in metadata["types"]],
            }
        )


class CardDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, card_id: str) -> Response:
        card, version, image = get_card_with_image(card_id)
        if card is None or version is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)
        metadata = get_card_version_metadata(version.id)
        edit_state = get_card_version_edit_state(version)
        card_groups = [
            card_group_summary_payload(group, card_id=card.id)
            for group in CardGroupService().get_groups_for_card(card.id)
        ]
        viewer_id = str(getattr(request.user, "pk", "")) if is_authenticated(request.user) else None
        deck_references = [
            {
                **deck_payload(deck),
                "card_reference": card_deck_reference_payload(deck, card_id=card.id),
            }
            for deck in DeckService().list_card_decks_for_viewer(card.id, viewer_id=viewer_id)[:CARD_DETAIL_DECK_REFERENCE_LIMIT]
        ]
        return Response(
            card_payload(
                card,
                version,
                image_url=card_image_asset_url(image, fallback_url=f"/cards/{card.id}/image"),
                metadata=metadata,
                edit_state=edit_state,
                card_groups=card_groups,
                deck_references=deck_references,
            )
        )


class CardGenerationsView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, card_id: str) -> Response:
        card = get_card(card_id)
        if card is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        versions = list_card_generations(card_id)
        if not versions:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        payloads = []
        for version in versions:
            image = get_card_image(version.id)
            metadata = get_card_version_metadata(version.id)
            edit_state = get_card_version_edit_state(version)
            payloads.append(
                card_payload(
                    card,
                    version,
                    image_url=card_image_asset_url(image, fallback_url=f"/cards/{card_id}/versions/{version.id}/image"),
                    metadata=metadata,
                    edit_state=edit_state,
                )
            )
        return Response(payloads)


class LatestCardVersionUpdateView(APIView):
    def patch(self, request: Request, card_id: str) -> Response:
        serializer = LatestVersionUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)

        try:
            updated = update_latest_card_version(
                card_id=card_id,
                updates=serializer.validated_update_payload(),
                restore_fields=serializer.validated_data["restore_fields"],
                restore_metadata_groups=serializer.validated_data["restore_metadata_groups"],
                unlock_fields=serializer.validated_data["unlock_fields"],
                unlock_metadata_groups=serializer.validated_data["unlock_metadata_groups"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if updated is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        card, version = updated
        image = get_card_image(version.id)
        metadata = get_card_version_metadata(version.id)
        edit_state = get_card_version_edit_state(version)
        return Response(
            card_payload(
                card,
                version,
                image_url=card_image_asset_url(image, fallback_url=f"/cards/{card_id}/versions/{version.id}/image"),
                metadata=metadata,
                edit_state=edit_state,
            )
        )


class CardVersionPromoteView(APIView):
    def post(self, _request: Request, card_id: str, version_id: str) -> Response:
        try:
            promoted = promote_card_version(card_id=card_id, version_id=version_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if promoted is None:
            return Response({"detail": "Card version not found"}, status=status.HTTP_404_NOT_FOUND)

        card, version = promoted
        image = get_card_image(version.id)
        metadata = get_card_version_metadata(version.id)
        edit_state = get_card_version_edit_state(version)
        return Response(
            card_payload(
                card,
                version,
                image_url=card_image_asset_url(image, fallback_url=f"/cards/{card.id}/versions/{version.id}/image"),
                metadata=metadata,
                edit_state=edit_state,
            )
        )


class CardVersionParseFlagView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, card_id: str, version_id: str) -> Response:
        serializer = CardVersionParseFlagCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            flag = create_parse_flag_for_card_version(
                card_id=card_id,
                version_id=version_id,
                submitted_by_id=str(getattr(request.user, "pk", "")),
                note=str(serializer.validated_data.get("note") or ""),
                items=[
                    ParseFlagItemInput(
                        property_key=str(item["property_key"]),
                        expected_value=str(item.get("expected_value") or ""),
                        note=str(item.get("note") or ""),
                    )
                    for item in serializer.validated_data["items"]
                ],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if flag is None:
            return Response({"detail": "Card version not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "id": flag.id,
                "card_version_id": flag.card_version_id,
                "item_count": flag.items.count(),
                "message": "Parse issue submitted.",
            },
            status=status.HTTP_201_CREATED,
        )


class LatestCardReparseView(APIView):
    def post(self, request: Request, card_id: str) -> Response:
        serializer = LatestCardReparseSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            result = CardActionService().queue_latest_version_reparse(
                card_id,
                template_id=serializer.validated_data.get("template_id"),
            )
        except CardReparseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if result is None:
            return Response({"detail": "Card not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "job_id": result.job_id,
                "message": result.message,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class CardImageView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, card_id: str) -> FileResponse:
        card, _version, image = get_card_with_image(card_id)
        if card is None or image is None:
            raise Http404("Card image not found")
        image_path = resolve_card_image_path(image)
        if image_path is None:
            raise Http404("Card image file is missing")
        return file_response(image_path, "Card image file is missing")


class CardVersionImageView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, card_id: str, version_id: str) -> FileResponse:
        if get_card(card_id) is None:
            raise Http404("Card not found")
        image = get_card_image(version_id)
        if image is None:
            raise Http404("Card image not found")
        image_path = resolve_card_image_path(image)
        if image_path is None:
            raise Http404("Card image file is missing")
        return file_response(image_path, "Card image file is missing")


class ImmutableCardImageView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, relative_path: str) -> FileResponse:
        return immutable_card_image_response(relative_path)


class SymbolAssetView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request, asset_path: str) -> FileResponse:
        return symbol_asset_response(asset_path)
