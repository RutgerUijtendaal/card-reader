from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.permissions import AuthEnabledOrSuperuserAllowed

from .services import MaintenanceService


class RebuildDatabaseView(APIView):
    permission_classes = [AuthEnabledOrSuperuserAllowed]

    def post(self, _request: Request) -> Response:
        result = MaintenanceService().rebuild_database()
        return Response({"message": result.message, "removed_paths": result.removed_paths})


class QueueLatestReparseView(APIView):
    permission_classes = [AuthEnabledOrSuperuserAllowed]

    def post(self, _request: Request) -> Response:
        result = MaintenanceService().queue_reparse_latest_versions()
        return Response({"message": result.message, "removed_paths": result.removed_paths})


class ClearStorageView(APIView):
    permission_classes = [AuthEnabledOrSuperuserAllowed]

    def post(self, request: Request) -> Response:
        result = MaintenanceService().clear_storage_data(
            include_images=bool(request.data.get("include_images", True)),
        )
        return Response({"message": result.message, "removed_paths": result.removed_paths})


class OpenStorageLocationView(APIView):
    permission_classes = [AuthEnabledOrSuperuserAllowed]

    def post(self, _request: Request) -> Response:
        result = MaintenanceService().open_storage_location()
        return Response({"message": result.message, "path": result.path})
