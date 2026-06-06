from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.responses import serializer_error
from card_reader_api.review.serializers import (
    ParseFlagItemsQuerySerializer,
    ParseFlagItemUpdateSerializer,
    parse_flag_payload,
    parse_flag_item_payload,
)
from card_reader_core.repositories.parse_flags import (
    count_open_parse_flag_items,
    list_parse_flags,
    update_parse_flag_item_status,
)


class ReviewSummaryView(APIView):
    def get(self, _request: Request) -> Response:
        return Response({"open_parse_flag_item_count": count_open_parse_flag_items()})


class ParseFlagItemsView(APIView):
    def get(self, request: Request) -> Response:
        serializer = ParseFlagItemsQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return serializer_error(serializer)
        page = list_parse_flags(
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
            item = update_parse_flag_item_status(
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
