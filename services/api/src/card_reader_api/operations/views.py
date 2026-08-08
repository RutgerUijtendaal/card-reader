from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.permissions import StaffAllowed
from card_reader_core.services.operations import OperationsOverviewService


class OperationsOverviewView(APIView):
    permission_classes = [StaffAllowed]

    def get(self, _request: Request) -> Response:
        return Response(OperationsOverviewService().build())
