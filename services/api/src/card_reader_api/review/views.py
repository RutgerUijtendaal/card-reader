from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.cards.serializers import card_payload
from card_reader_api.common.auth_access import card_pool_scope_for_user
from card_reader_api.common.responses import serializer_error
from card_reader_api.review.serializers import (
    ParseFlagItemsQuerySerializer,
    ParseFlagItemUpdateSerializer,
    ReviewConfidenceCardsQuerySerializer,
    parse_flag_payload,
    parse_flag_item_payload,
)
from card_reader_core.repositories.cards import list_review_cards
from card_reader_core.repositories.parse_flags import (
    count_open_parse_flag_items,
    list_parse_flags,
)
from card_reader_core.services.parse_flags import review_parse_flag_item


class ReviewSummaryView(APIView):
    def get(self, request: Request) -> Response:
        return Response(
            {
                "open_parse_flag_item_count": count_open_parse_flag_items(
                    card_pool_scope=card_pool_scope_for_user(request.user)
                )
            }
        )


class ReviewConfidenceCardsView(APIView):
    def get(self, request: Request) -> Response:
        serializer = ReviewConfidenceCardsQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return serializer_error(serializer)
        page = list_review_cards(
            card_pool_scope=card_pool_scope_for_user(request.user),
            max_confidence=0.8,
            page=serializer.validated_data["page"],
            page_size=serializer.validated_data["page_size"],
        )
        results = [
            card_payload(
                row.version.card,
                row.version,
                image_url=card_image_asset_url(
                    row.image,
                    fallback_url=f"/cards/{row.version.card.id}/image",
                ),
                metadata={
                    "keywords": row.keywords,
                    "tags": row.tags,
                    "symbols": row.symbols,
                    "types": row.types,
                },
            )
            for row in page.results
        ]
        return Response(
            {
                "count": page.count,
                "next_page": page.page + 1 if page.page * page.page_size < page.count else None,
                "previous_page": page.page - 1 if page.page > 1 else None,
                "page": page.page,
                "page_size": page.page_size,
                "results": results,
            }
        )


class ParseFlagItemsView(APIView):
    def get(self, request: Request) -> Response:
        serializer = ParseFlagItemsQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return serializer_error(serializer)
        page = list_parse_flags(
            card_pool_scope=card_pool_scope_for_user(request.user),
            status=serializer.validated_data["status"],
            page=serializer.validated_data["page"],
            page_size=serializer.validated_data["page_size"],
        )
        return Response(
            {
                "count": page.count,
                "next_page": page.page + 1 if page.page * page.page_size < page.count else None,
                "previous_page": page.page - 1 if page.page > 1 else None,
                "page": page.page,
                "page_size": page.page_size,
                "results": [parse_flag_payload(flag) for flag in page.results],
            }
        )


class ParseFlagItemDetailView(APIView):
    def patch(self, request: Request, item_id: str) -> Response:
        serializer = ParseFlagItemUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            item = review_parse_flag_item(
                item_id=item_id,
                status=serializer.validated_data["status"],
                reviewed_by_id=str(getattr(request.user, "pk", "")),
                review_note=str(serializer.validated_data.get("review_note") or ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if item is None:
            return Response({"detail": "Parse flag item not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(parse_flag_item_payload(item))
