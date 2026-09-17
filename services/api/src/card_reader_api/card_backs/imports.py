from __future__ import annotations

from uuid import UUID

from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_core.models import CardBackImportReceipt
from card_reader_core.services.cards import get_card_back_import_result, import_card_back

from .serializers import card_back_payload


class ImportKeySerializer(serializers.Serializer[dict[str, object]]):
    client_request_id = serializers.UUIDField()


class ImportItemSerializer(ImportKeySerializer):
    file = serializers.FileField()
    label = serializers.CharField(allow_blank=False)  # type: ignore[assignment]
    hero_card_id = serializers.CharField(required=False, allow_null=True, default=None)
    expected_override_id = serializers.CharField(required=False, allow_null=True, default=None)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if attrs.get("hero_card_id") and "expected_override_id" not in self.initial_data:
            raise serializers.ValidationError("The expected hero override must be supplied.")
        return attrs


def import_result_payload(receipt: CardBackImportReceipt) -> dict[str, object]:
    if receipt.error:
        return {"outcome": "rejected", "detail": receipt.error}
    if receipt.card_back is None:
        return {
            "outcome": "deleted",
            "detail": "This request's card back was deleted; it will not be recreated.",
        }
    return {
        "outcome": "succeeded",
        "asset": card_back_payload(receipt.card_back),
        "hero_card_id": receipt.hero_card_id,
    }


class AdminCardBackImportView(APIView):
    def post(self, request: Request) -> Response:
        key_serializer = ImportKeySerializer(data=request.data)
        key_serializer.is_valid(raise_exception=True)
        request_id = key_serializer.validated_data["client_request_id"]
        owner_id = str(request.user.pk)
        existing = get_card_back_import_result(owner_id, request_id)
        if existing is not None:
            return Response(import_result_payload(existing))

        serializer = ImportItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"outcome": "invalid", "detail": serializer.errors}, status=400)
        data = serializer.validated_data
        upload = data["file"]
        receipt, created = import_card_back(
            owner_id=owner_id,
            client_request_id=request_id,
            filename=upload.name,
            chunks=upload.chunks(),
            label=data["label"],
            hero_card_id=data["hero_card_id"],
            expected_override_id=data["expected_override_id"],
        )
        return Response(
            import_result_payload(receipt), status=201 if created and not receipt.error else 200
        )


class AdminCardBackImportResultView(APIView):
    def get(self, request: Request, client_request_id: UUID) -> Response:
        receipt = get_card_back_import_result(str(request.user.pk), client_request_id)
        if receipt is None:
            return Response({"detail": "No completed outcome found."}, status=404)
        return Response(import_result_payload(receipt))
