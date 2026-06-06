from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.cards.public_urls import card_image_asset_url
from card_reader_api.cards.serializers import card_payload
from card_reader_api.common.permissions import AuthEnabledOrStaffAllowed
from card_reader_api.common.responses import bad_request, not_found, serializer_error
from card_reader_api.content_versions.serializers import ContentVersionUpdateSerializer, content_version_payload
from card_reader_core.repositories.cards import list_cards_for_content_version
from card_reader_core.repositories.content_versions import list_content_versions, update_content_version


class ContentVersionListView(APIView):
    permission_classes = [AuthEnabledOrStaffAllowed]

    def get(self, _request: Request) -> Response:
        return Response([content_version_payload(version) for version in list_content_versions()])


class ContentVersionCardsView(APIView):
    permission_classes = [AuthEnabledOrStaffAllowed]

    def get(self, _request: Request, version_id: str) -> Response:
        versions = {version.id for version in list_content_versions()}
        if version_id not in versions:
            return not_found("Content version not found")

        payloads = []
        for row in list_cards_for_content_version(version_id):
            payloads.append(
                card_payload(
                    row.version.card,
                    row.version,
                    image_url=card_image_asset_url(
                        row.image,
                        fallback_url=f"/cards/{row.version.card.id}/versions/{row.version.id}/image",
                    ),
                    metadata={
                        "keywords": row.keywords,
                        "tags": row.tags,
                        "symbols": row.symbols,
                        "types": row.types,
                    },
                )
            )
        return Response(payloads)


class ContentVersionDetailView(APIView):
    permission_classes = [AuthEnabledOrStaffAllowed]

    def patch(self, request: Request, version_id: str) -> Response:
        serializer = ContentVersionUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return serializer_error(serializer)
        try:
            updated = update_content_version(
                version_id,
                version_number=serializer.validated_data.get("version_number"),
                description=serializer.validated_data.get("description"),
            )
        except ValueError as exc:
            return bad_request(str(exc))
        if updated is None:
            return not_found("Content version not found")
        return Response(content_version_payload(updated))
