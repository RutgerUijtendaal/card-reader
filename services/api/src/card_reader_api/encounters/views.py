from __future__ import annotations

from uuid import UUID

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.auth_access import can_access_admin
from card_reader_api.common.permissions import StaffAllowed
from card_reader_api.common.urls import build_public_api_url
from card_reader_api.exports.tts_cards import encode_tts_card_export
from card_reader_api.cards.grouped_gallery import grouped_gallery_payload
from card_reader_api.cards.query_params import card_filter_query_data
from card_reader_api.cards.serializers import CardFiltersQuerySerializer
from card_reader_core.repositories import encounters
from card_reader_core.services.encounters import EncounterService, MINIMUM_ENCOUNTER_CARDS
from card_reader_core.services.exports import TtsCardExportError, TtsCardExportService

from .serializers import (
    EncounterListSerializer,
    EncounterWriteSerializer,
    encounter_payload,
    encounter_summaries,
)


class EncounterRulesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"minimum_cards": MINIMUM_ENCOUNTER_CARDS, "card_pool": "evil"})


class EncounterBossPickerView(APIView):
    permission_classes = [StaffAllowed]

    def get(self, request: Request) -> Response:
        data = card_filter_query_data(request, include_list_controls=True)
        data.update(
            card_pool="evil",
            card_roles=["boss"],
            card_role_match="any",
            lifecycle_status="active",
            show_groups=True,
        )
        serializer = CardFiltersQuerySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(
            grouped_gallery_payload(serializer.validated_list_filters(), anchor_role="boss", require_active_pool_members=True)
        )


class PublicEncounterListView(APIView):
    permission_classes = [AllowAny]
    staff = False

    def get(self, request: Request) -> Response:
        params = EncounterListSerializer(
            data={
                **request.query_params.dict(),
                "factions": request.query_params.getlist("factions"),
            }
        )
        params.is_valid(raise_exception=True)
        data = params.validated_data
        page, size = data["page"], data["page_size"]
        count, records = encounters.list_encounters(
            staff=self.staff,
            minimum_cards=MINIMUM_ENCOUNTER_CARDS,
            query=data["q"],
            factions=data["factions"],
            page=page,
            page_size=size,
        )
        return Response(
            {
                "count": count,
                "page": page,
                "page_size": size,
                "next_page": page + 1 if page * size < count else None,
                "previous_page": page - 1 if page > 1 else None,
                "results": encounter_summaries(records),
            }
        )


class StaffEncounterListView(PublicEncounterListView):
    permission_classes = [StaffAllowed]
    staff = True

    def post(self, request: Request) -> Response:
        try:
            key = UUID(request.headers.get("Idempotency-Key", ""))
        except ValueError:
            return Response({"detail": "Idempotency-Key must be a UUID."}, status=400)
        creator = str(request.user.pk)
        existing, used = encounters.creation_result(creator, key)
        if existing:
            return Response(encounter_payload(existing))
        if used:
            return Response({"detail": "This Encounter was deleted."}, status=410)
        serializer = EncounterWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            record, created = EncounterService().create(creator, key, serializer.validated_data)
        except encounters.EncounterDeleted as exc:
            return Response({"detail": str(exc)}, status=410)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(encounter_payload(record), status=201 if created else 200)


class PublicEncounterDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, encounter_id: str) -> Response:
        record = encounters.public_queryset(MINIMUM_ENCOUNTER_CARDS).filter(pk=encounter_id).first()
        return Response(encounter_payload(record)) if record else Response(status=404)


class StaffEncounterDetailView(APIView):
    permission_classes = [StaffAllowed]

    def get(self, request: Request, encounter_id: str) -> Response:
        record = encounters.get_encounter(encounter_id)
        return Response(encounter_payload(record)) if record else Response(status=404)

    def patch(self, request: Request, encounter_id: str) -> Response:
        record = encounters.get_encounter(encounter_id)
        if record is None:
            return Response(status=404)
        serializer = EncounterWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if "revision" not in serializer.validated_data:
            return Response({"detail": "Revision is required."}, status=400)
        try:
            updated = EncounterService().update(
                record, serializer.validated_data, serializer.validated_data["revision"]
            )
        except encounters.EncounterConflict as exc:
            return Response({"detail": str(exc)}, status=409)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(encounter_payload(updated))

    def delete(self, request: Request, encounter_id: str) -> Response:
        if encounters.get_encounter(encounter_id) is None:
            return Response(status=404)
        try:
            revision = int(request.headers.get("If-Match", ""))
        except ValueError:
            return Response({"detail": "If-Match revision is required."}, status=400)
        try:
            encounters.delete_encounter(encounter_id, revision)
        except encounters.EncounterConflict as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(status=204)


class EncounterCreationLookupView(APIView):
    permission_classes = [StaffAllowed]

    def get(self, request: Request, key: UUID) -> Response:
        record, used = encounters.creation_result(str(request.user.pk), key)
        return (
            Response(encounter_payload(record)) if record else Response(status=410 if used else 404)
        )


class EncounterTtsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, encounter_id: str) -> Response:
        query = (
            encounters.encounter_queryset()
            if can_access_admin(request.user)
            else encounters.public_queryset(MINIMUM_ENCOUNTER_CARDS)
        )
        record = query.filter(pk=encounter_id).first()
        if record is None:
            return Response(status=404)
        try:
            data = TtsCardExportService().build_encounter_export(record)

            def absolute_url(path: str) -> str:
                return build_public_api_url(request, path)

            export = encode_tts_card_export(data, absolute_url=absolute_url)
        except TtsCardExportError as exc:
            response = Response(
                {"detail": str(exc)}, status=503 if exc.code == "sheets_unavailable" else 409
            )
            if response.status_code == 503:
                response["Retry-After"] = "2"
            return response
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(
            {
                "encoded_payload": export.encoded_payload,
                "exported_count": export.exported_count,
                "skipped_count": export.skipped_count,
                "sheet_count": export.sheet_count,
            }
        )
