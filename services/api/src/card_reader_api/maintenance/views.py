from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.cards.serializers import CardFiltersQuerySerializer
from card_reader_api.common.permissions import SuperuserAllowed

from .services import MaintenanceService


class BackfillMetadataSuggestionsView(APIView):
    permission_classes = [SuperuserAllowed]

    def post(self, _request: Request) -> Response:
        result = MaintenanceService().backfill_metadata_suggestions()
        return Response({"message": result.message, "removed_paths": result.removed_paths})


class ConvertCardImagesToWebpView(APIView):
    permission_classes = [SuperuserAllowed]

    def post(self, _request: Request) -> Response:
        result = MaintenanceService().convert_card_images_to_webp()
        conversion = result.conversion
        return Response(
            {
                "message": result.message,
                "removed_paths": result.removed_paths,
                "converted": conversion.converted,
                "already_webp": conversion.already_webp,
                "missing": conversion.missing,
                "failed": conversion.failed,
                "bytes_before": conversion.bytes_before,
                "bytes_after": conversion.bytes_after,
                "failures": [
                    {
                        "image_id": failure.image_id,
                        "path": failure.path,
                        "detail": failure.detail,
                    }
                    for failure in conversion.failures
                ],
            }
        )


class QueueLatestReparseView(APIView):
    permission_classes = [SuperuserAllowed]

    def post(self, _request: Request) -> Response:
        result = MaintenanceService().queue_reparse_latest_versions()
        return Response({"message": result.message, "removed_paths": result.removed_paths})


class QueueFilteredLatestReparseView(APIView):
    permission_classes = [SuperuserAllowed]

    def post(self, request: Request) -> Response:
        serializer = CardFiltersQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = MaintenanceService().queue_reparse_latest_versions_by_filters(
            filters=serializer.validated_filters(),
        )
        return Response({"message": result.message, "removed_paths": result.removed_paths})
