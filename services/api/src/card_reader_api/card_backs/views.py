from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.card_backs.serializers import (
    CardBackUploadSerializer,
    CardBackDefaultUpdateSerializer,
    card_back_payload,
    current_card_back_payload,
    public_card_back_payload,
)
from card_reader_api.common.responses import bad_request, serializer_error
from card_reader_core.models import PLAYER_CARD_POOL
from card_reader_core.services.card_backs import (
    clear_faction_default,
    clear_pool_default,
    clear_role_default,
    get_faction_card_back_defaults,
    get_pool_card_back_defaults,
    get_role_card_back_defaults,
    list_card_back_assets,
    set_faction_default,
    set_pool_default,
    set_role_default,
    upload_card_back_asset,
)


class CurrentCardBackView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        return Response(current_card_back_payload(get_pool_card_back_defaults()[PLAYER_CARD_POOL]))


class CardBackDefaultsView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        defaults = get_pool_card_back_defaults()
        return Response(
            {
                card_pool: None if card_back is None else public_card_back_payload(card_back)
                for card_pool, card_back in defaults.items()
            }
        )


class CardBackFactionDefaultsView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        defaults = get_faction_card_back_defaults()
        return Response(
            {
                faction: None if card_back is None else public_card_back_payload(card_back)
                for faction, card_back in defaults.items()
            }
        )


class CardBackRoleDefaultsView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request: Request) -> Response:
        defaults = get_role_card_back_defaults()
        return Response(
            {
                role: None if card_back is None else public_card_back_payload(card_back)
                for role, card_back in defaults.items()
            }
        )


class AdminCardBackListView(APIView):
    def get(self, _request: Request) -> Response:
        return Response([card_back_payload(card_back) for card_back in list_card_back_assets()])


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
            card_back = upload_card_back_asset(
                filename=upload.name,
                chunks=upload.chunks(),
                label=serializer.validated_data.get("label"),
            )
        except ValueError as exc:
            return bad_request(str(exc))

        return Response(card_back_payload(card_back), status=status.HTTP_201_CREATED)


class AdminCardBackDefaultView(APIView):
    def put(self, request: Request, card_pool: str) -> Response:
        serializer = CardBackDefaultUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        card_back_id = serializer.validated_data["card_back_id"]
        try:
            if card_back_id is None:
                clear_pool_default(card_pool)
                return Response(status=status.HTTP_204_NO_CONTENT)
            row = set_pool_default(card_pool, str(card_back_id))
        except ValueError as exc:
            return bad_request(str(exc))
        return Response(public_card_back_payload(row.card_back))


class AdminCardBackFactionDefaultView(APIView):
    def put(self, request: Request, faction: str) -> Response:
        serializer = CardBackDefaultUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        card_back_id = serializer.validated_data["card_back_id"]
        try:
            if card_back_id is None:
                clear_faction_default(faction)
                return Response(status=status.HTTP_204_NO_CONTENT)
            row = set_faction_default(faction, str(card_back_id))
        except ValueError as exc:
            return bad_request(str(exc))
        return Response(public_card_back_payload(row.card_back))


class AdminCardBackRoleDefaultView(APIView):
    def put(self, request: Request, role: str) -> Response:
        serializer = CardBackDefaultUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        card_back_id = serializer.validated_data["card_back_id"]
        try:
            if card_back_id is None:
                clear_role_default(role)
                return Response(status=status.HTTP_204_NO_CONTENT)
            row = set_role_default(role, str(card_back_id))
        except ValueError as exc:
            return bad_request(str(exc))
        return Response(public_card_back_payload(row.card_back))
