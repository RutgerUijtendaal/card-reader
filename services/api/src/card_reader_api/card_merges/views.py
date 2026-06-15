from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.card_merges.serializers import CardMergeRequestSerializer, card_merge_preview_payload
from card_reader_api.common.permissions import StaffAllowed
from card_reader_core.services.card_merges import CardMergeError, merge_cards, preview_card_merge


class CardMergePreviewView(APIView):
    permission_classes = [StaffAllowed]

    def post(self, request: Request) -> Response:
        serializer = CardMergeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            preview = preview_card_merge(
                target_card_id=str(serializer.validated_data["target_card_id"]),
                source_card_ids=[str(card_id) for card_id in serializer.validated_data["source_card_ids"]],
            )
        except CardMergeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(card_merge_preview_payload(preview))


class CardMergeApplyView(APIView):
    permission_classes = [StaffAllowed]

    def post(self, request: Request) -> Response:
        serializer = CardMergeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            preview = merge_cards(
                target_card_id=str(serializer.validated_data["target_card_id"]),
                source_card_ids=[str(card_id) for card_id in serializer.validated_data["source_card_ids"]],
            )
        except CardMergeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Card merge completed.", "preview": card_merge_preview_payload(preview)})
