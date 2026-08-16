from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.auth_access import card_pool_scope_for_user
from card_reader_api.common.responses import paginated_payload, serializer_error
from card_reader_api.review.serializers import (
    ClassificationReviewItemsQuerySerializer,
    ClassificationReviewItemUpdateSerializer,
    ParseFlagItemsQuerySerializer,
    ParseFlagItemUpdateSerializer,
    classification_review_item_payload,
    parse_flag_payload,
    parse_flag_item_payload,
)
from card_reader_core.repositories.classification_reviews import (
    count_open_classification_review_items,
    list_classification_review_items,
)
from card_reader_core.repositories.parse_flags import (
    count_open_parse_flag_items,
    list_parse_flags,
)
from card_reader_core.services.classification_reviews import review_classification_item
from card_reader_core.services.parse_flags import review_parse_flag_item


class ReviewSummaryView(APIView):
    def get(self, request: Request) -> Response:
        card_pool_scope = card_pool_scope_for_user(request.user)
        open_parse_flag_item_count = count_open_parse_flag_items(
            card_pool_scope=card_pool_scope
        )
        open_classification_review_count = count_open_classification_review_items(
            card_pool_scope=card_pool_scope
        )
        return Response(
            {
                "open_parse_flag_item_count": open_parse_flag_item_count,
                "open_classification_review_count": open_classification_review_count,
                "open_review_count": (
                    open_parse_flag_item_count + open_classification_review_count
                ),
            }
        )


class ClassificationReviewItemsView(APIView):
    def get(self, request: Request) -> Response:
        serializer = ClassificationReviewItemsQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return serializer_error(serializer)
        page = list_classification_review_items(
            card_pool_scope=card_pool_scope_for_user(request.user),
            status=serializer.validated_data["status"],
            page=serializer.validated_data["page"],
            page_size=serializer.validated_data["page_size"],
        )
        return Response(
            paginated_payload(
                page,
                [classification_review_item_payload(item) for item in page.results],
            )
        )


class ClassificationReviewItemDetailView(APIView):
    def patch(self, request: Request, item_id: str) -> Response:
        serializer = ClassificationReviewItemUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        card_pool_scope = card_pool_scope_for_user(request.user)
        try:
            item = review_classification_item(
                item_id=item_id,
                status=serializer.validated_data["status"],
                reviewed_by_id=str(getattr(request.user, "pk", "")),
                card_pool_scope=card_pool_scope,
                review_note=str(serializer.validated_data.get("review_note") or ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if item is None:
            return Response(
                {"detail": "Classification review item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(classification_review_item_payload(item))


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
            paginated_payload(
                page,
                [parse_flag_payload(flag) for flag in page.results],
            )
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
