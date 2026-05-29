from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.card_groups.serializers import (
    CardGroupWriteSerializer,
    card_group_admin_payload,
    card_group_detail_payload,
    serializer_error,
)
from card_reader_api.cards.serializers import CardFiltersQuerySerializer
from card_reader_api.common.permissions import AuthEnabledOrStaffAllowed
from card_reader_core.services.card_groups import CardGroupMemberInput, CardGroupService


class PublicCardGroupDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, group_id: str) -> Response:
        serializer = CardFiltersQuerySerializer(data=_lifecycle_query_data(request))
        if not serializer.is_valid():
            return serializer_error(serializer)
        lifecycle_status = serializer.validated_filters()["lifecycle_status"]
        group = CardGroupService().get_group(group_id)
        if group is None:
            return Response({"detail": "Card group not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(card_group_detail_payload(group, lifecycle_status=lifecycle_status))


class StaffCardGroupListCreateView(APIView):
    permission_classes = [AuthEnabledOrStaffAllowed]

    def get(self, _request: Request) -> Response:
        groups = CardGroupService().list_groups()
        return Response([card_group_admin_payload(group) for group in groups])

    def post(self, request: Request) -> Response:
        serializer = CardGroupWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error(serializer)
        anchor_card_id = serializer.validated_data.get("anchor_card_id")
        members = serializer.validated_data.get("members")
        if not anchor_card_id or not members:
            return Response({"detail": "anchor_card_id and members are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            group = CardGroupService().create_group(
                name=serializer.validated_data.get("name"),
                anchor_card_id=anchor_card_id,
                members=[CardGroupMemberInput(**member) for member in members],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(card_group_admin_payload(group))


class StaffCardGroupDetailView(APIView):
    permission_classes = [AuthEnabledOrStaffAllowed]

    def get(self, _request: Request, group_id: str) -> Response:
        group = CardGroupService().get_group(group_id)
        if group is None:
            return Response({"detail": "Card group not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(card_group_admin_payload(group))

    def patch(self, request: Request, group_id: str) -> Response:
        serializer = CardGroupWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return serializer_error(serializer)
        members = serializer.validated_data.get("members")
        try:
            group = CardGroupService().update_group(
                group_id=group_id,
                name=serializer.validated_data.get("name"),
                anchor_card_id=serializer.validated_data.get("anchor_card_id"),
                members=None if members is None else [CardGroupMemberInput(**member) for member in members],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if group is None:
            return Response({"detail": "Card group not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(card_group_admin_payload(group))

    def delete(self, _request: Request, group_id: str) -> Response:
        deleted = CardGroupService().delete_group(group_id=group_id)
        if not deleted:
            return Response({"detail": "Card group not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _lifecycle_query_data(request: Request) -> dict[str, object]:
    lifecycle_status = request.query_params.get("lifecycle_status")
    if lifecycle_status is None:
        return {}
    return {"lifecycle_status": lifecycle_status}
