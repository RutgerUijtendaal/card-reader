from __future__ import annotations

from typing import Any

from django.urls import reverse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.responses import serializer_error
from card_reader_api.common.permissions import StaffAllowed
from card_reader_api.operations.serializers import (
    OperationsOverviewQuerySerializer,
    OperationsQueueQuerySerializer,
)
from card_reader_core.services.operations import (
    OperationsOverviewService,
    OperationsQueueNotFoundError,
)


class OperationsOverviewView(APIView):
    permission_classes = [StaffAllowed]

    def get(self, request: Request) -> Response:
        serializer = OperationsOverviewQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return serializer_error(serializer)
        payload = OperationsOverviewService().build(
            include_items=serializer.validated_data["include_items"],
        )
        _add_transport_links(payload)
        return Response(payload)


class OperationsQueueView(APIView):
    permission_classes = [StaffAllowed]

    def get(self, request: Request, queue_key: str) -> Response:
        serializer = OperationsQueueQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            payload = OperationsOverviewService().build_queue_page(
                queue_key=queue_key,
                page=serializer.validated_data["page"],
                page_size=serializer.validated_data["page_size"],
            )
        except OperationsQueueNotFoundError:
            return Response(
                {"detail": "Operations queue not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        _add_item_transport_links(queue_key=queue_key, items=payload["results"])
        return Response(payload)


def _add_transport_links(payload: dict[str, Any]) -> None:
    for queue in payload["queues"]:
        _add_item_transport_links(queue_key=queue["key"], items=queue["items"])


def _add_item_transport_links(*, queue_key: str, items: list[dict[str, Any]]) -> None:
    if queue_key != "developer-data-builds":
        return
    for item in items:
        if item["native_status"] == "succeeded":
            item["links"] = [
                {
                    "label": "Download lock file",
                    "href": reverse(
                        "developer-data-build-lock",
                        kwargs={"build_id": item["id"]},
                    ),
                }
            ]
