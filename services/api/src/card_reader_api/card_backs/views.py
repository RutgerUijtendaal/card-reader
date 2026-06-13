from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.card_backs.serializers import (
    CardBackUploadSerializer,
    card_back_payload,
    current_card_back_payload,
)
from card_reader_api.common.responses import bad_request, not_found, serializer_error
from card_reader_core.services.card_backs import CardBackService


class CurrentCardBackView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        return Response(current_card_back_payload(CardBackService().get_current()))


class AdminCardBackListView(APIView):
    def get(self, _request: Request) -> Response:
        return Response([card_back_payload(card_back) for card_back in CardBackService().list_history()])


class AdminCardBackUploadView(APIView):
    def post(self, request: Request) -> Response:
        serializer = CardBackUploadSerializer(
            data={
                "file": request.FILES.get("file"),
                "label": request.data.get("label"),
            }
        )
        if not serializer.is_valid():
            return serializer_error(serializer)

        upload = serializer.validated_data["file"]
        try:
            card_back = CardBackService().upload(
                filename=upload.name,
                chunks=upload.chunks(),
                label=serializer.validated_data.get("label"),
            )
        except ValueError as exc:
            return bad_request(str(exc))

        return Response(card_back_payload(card_back), status=status.HTTP_201_CREATED)


class AdminCardBackActivateView(APIView):
    def post(self, _request: Request, card_back_id: str) -> Response:
        try:
            card_back = CardBackService().activate(card_back_id)
        except ValueError as exc:
            return bad_request(str(exc))
        if card_back is None:
            return not_found("Card back not found")
        return Response(card_back_payload(card_back))
