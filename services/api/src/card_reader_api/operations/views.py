from __future__ import annotations

from typing import Any

from django.urls import reverse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.permissions import StaffAllowed
from card_reader_core.services.operations import OperationsOverviewService


class OperationsOverviewView(APIView):
    permission_classes = [StaffAllowed]

    def get(self, _request: Request) -> Response:
        payload = OperationsOverviewService().build()
        _add_transport_links(payload)
        return Response(payload)


def _add_transport_links(payload: dict[str, Any]) -> None:
    for queue in payload["queues"]:
        if queue["key"] != "developer-data-builds":
            continue
        for item in queue["items"]:
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
