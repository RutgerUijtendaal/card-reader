from __future__ import annotations

from uuid import UUID

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.auth_access import can_access_admin, is_authenticated
from card_reader_api.common.permissions import AuthenticatedAllowed, StaffAllowed
from card_reader_api.common.urls import build_public_api_url
from card_reader_api.exports.tts_cards import encode_tts_card_export
from card_reader_api.cards.grouped_gallery import grouped_gallery_payload
from card_reader_api.cards.query_params import card_filter_query_data
from card_reader_api.cards.serializers import CardFiltersQuerySerializer
from card_reader_core.repositories import encounters
from card_reader_core.services.encounters import (
    EncounterActor,
    EncounterService,
    MINIMUM_ENCOUNTER_CARDS,
)
from card_reader_core.services.exports import TtsCardExportError, TtsCardExportService

from .serializers import (
    EncounterListSerializer,
    EncounterWriteSerializer,
    encounter_payload,
    encounter_summaries,
)


def request_actor(request: Request) -> EncounterActor:
    return EncounterActor(
        user_id=str(request.user.pk) if is_authenticated(request.user) else None,
        is_staff=can_access_admin(request.user),
    )


class EncounterRulesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"minimum_cards": MINIMUM_ENCOUNTER_CARDS, "card_pool": "evil"})


class EncounterBossPickerView(APIView):
    permission_classes = [AuthenticatedAllowed]

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
            grouped_gallery_payload(
                serializer.validated_list_filters(),
                anchor_role="boss",
                require_active_pool_members=True,
            )
        )


class PublicEncounterListView(APIView):
    permission_classes = [AllowAny]
    staff = False
    mine = False

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
            owner_id=str(request.user.pk) if self.mine else None,
            is_official=data.get("is_official"),
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
                "results": encounter_summaries(records, actor=request_actor(request)),
            }
        )


class MyEncounterListView(PublicEncounterListView):
    permission_classes = [AuthenticatedAllowed]
    mine = True

    def post(self, request: Request) -> Response:
        actor = request_actor(request)
        try:
            EncounterService.check_official_field(request.data, actor)
        except encounters.EncounterForbidden as exc:
            return Response({"detail": str(exc)}, status=403)
        try:
            key = UUID(request.headers.get("Idempotency-Key", ""))
        except ValueError:
            return Response({"detail": "Idempotency-Key must be a UUID."}, status=400)
        creator = str(request.user.pk)
        existing, used = encounters.creation_result(creator, key)
        if existing:
            return Response(encounter_payload(existing, actor=request_actor(request)))
        if used:
            return Response({"detail": "This Encounter was deleted."}, status=410)
        serializer = EncounterWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            record, created = EncounterService().create(
                creator, key, serializer.validated_data, actor=actor
            )
        except encounters.EncounterDeleted as exc:
            return Response({"detail": str(exc)}, status=410)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            encounter_payload(record, actor=request_actor(request)), status=201 if created else 200
        )


class StaffEncounterListView(MyEncounterListView):
    permission_classes = [StaffAllowed]
    staff = True
    mine = False


class PublicEncounterDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, encounter_id: str) -> Response:
        record = EncounterService().get_for_viewer(encounter_id, actor=request_actor(request))
        return (
            Response(encounter_payload(record, actor=request_actor(request)))
            if record
            else Response(status=404)
        )


class MyEncounterDetailView(APIView):
    permission_classes = [AuthenticatedAllowed]

    def get(self, request: Request, encounter_id: str) -> Response:
        record = EncounterService().get_for_viewer(
            encounter_id, actor=request_actor(request), management=True
        )
        return (
            Response(encounter_payload(record, actor=request_actor(request)))
            if record
            else Response(status=404)
        )

    def patch(self, request: Request, encounter_id: str) -> Response:
        record = EncounterService().get_for_viewer(
            encounter_id, actor=request_actor(request), management=True
        )
        if record is None:
            return Response(status=404)
        serializer = EncounterWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if "revision" not in serializer.validated_data:
            return Response({"detail": "Revision is required."}, status=400)
        try:
            updated = EncounterService().update(
                record,
                serializer.validated_data,
                serializer.validated_data["revision"],
                actor=request_actor(request),
            )
        except encounters.EncounterForbidden as exc:
            return Response({"detail": str(exc)}, status=403)
        except encounters.EncounterConflict as exc:
            return Response({"detail": str(exc)}, status=409)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(encounter_payload(updated, actor=request_actor(request)))

    def delete(self, request: Request, encounter_id: str) -> Response:
        if (
            EncounterService().get_for_viewer(
                encounter_id, actor=request_actor(request), management=True
            )
            is None
        ):
            return Response(status=404)
        try:
            revision = int(request.headers.get("If-Match", ""))
        except ValueError:
            return Response({"detail": "If-Match revision is required."}, status=400)
        try:
            EncounterService().delete(
                encounter_id,
                revision,
                actor=request_actor(request),
            )
        except encounters.EncounterForbidden as exc:
            return Response({"detail": str(exc)}, status=403)
        except encounters.EncounterConflict as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(status=204)


class StaffEncounterDetailView(MyEncounterDetailView):
    permission_classes = [StaffAllowed]


class EncounterCreationLookupView(APIView):
    permission_classes = [AuthenticatedAllowed]

    def get(self, request: Request, key: UUID) -> Response:
        record, used = encounters.creation_result(str(request.user.pk), key)
        return (
            Response(encounter_payload(record, actor=request_actor(request)))
            if record
            else Response(status=410 if used else 404)
        )


class StaffEncounterCreationLookupView(EncounterCreationLookupView):
    permission_classes = [StaffAllowed]


class StaffEncounterBossPickerView(EncounterBossPickerView):
    permission_classes = [StaffAllowed]


class EncounterTtsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, encounter_id: str) -> Response:
        record = EncounterService().get_for_viewer(
            encounter_id, actor=request_actor(request), export=True
        )
        if record is None:
            return Response(status=404)
        try:
            data = TtsCardExportService().build_encounter_export(
                record, sideboard_id=request.query_params.get("sideboard_id")
            )

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
