from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.common.responses import bad_request, not_found, serializer_error
from card_reader_api.imports.serializers import (
    ImportUploadSerializer,
    content_version_payload,
    import_detail_payload,
    import_job_payload,
)
from card_reader_core.repositories.content_versions import get_current_content_version
from card_reader_api.imports.creation import (
    ImportAdmissionConflict,
    ImportAdmissionRejected,
    ImportAdmissionUncertain,
    ImportUploadAdmission,
)
from card_reader_core.repositories.import_jobs import fetch_items_for_job, fetch_job, list_import_jobs
from card_reader_core.services.imports import ImportService


class ImportListView(APIView):
    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status", "all")
        if status_filter not in {"all", "active"}:
            return bad_request("status must be either 'all' or 'active'")
        jobs = list_import_jobs(active_only=status_filter == "active")
        return Response([import_job_payload(job) for job in jobs])


class CurrentContentVersionView(APIView):
    def get(self, _request: Request) -> Response:
        return Response(content_version_payload(get_current_content_version()))


class ImportUploadView(APIView):
    def post(self, request: Request) -> Response:
        upload_data: dict[str, object] = {
            "options_json": request.data.get("options_json", "{}"),
            "files": request.FILES.getlist("files"),
            "card_role_mode": request.data.get("card_role_mode", "automatic"),
            "card_role_override": request.data.get("card_role_override", "[]"),
            "card_faction_mode": request.data.get("card_faction_mode", "automatic"),
            "card_faction_override": request.data.get("card_faction_override", "[]"),
            "card_mana_family_mode": request.data.get(
                "card_mana_family_mode", "automatic"
            ),
            "card_mana_family_override": request.data.get(
                "card_mana_family_override", "[]"
            ),
        }
        for required_field in (
            "creation_key",
            "template_id",
            "content_version_base",
            "content_version_description",
            "card_pool",
        ):
            if required_field in request.data:
                upload_data[required_field] = request.data[required_field]

        serializer = ImportUploadSerializer(data=upload_data)
        if not serializer.is_valid():
            return serializer_error(serializer)

        try:
            result = ImportUploadAdmission().admit(serializer.validated_data)
        except ImportAdmissionConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ImportAdmissionRejected as exc:
            return bad_request(str(exc))
        except ImportAdmissionUncertain as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {
                **import_job_payload(result.job),
                "job_id": result.job.id,
                "idempotent_replay": result.idempotent_replay,
            },
            status=status.HTTP_200_OK if result.idempotent_replay else status.HTTP_201_CREATED,
        )


class ImportCreationKeyView(APIView):
    def get(self, _request: Request, creation_key: object) -> Response:
        job = ImportService().get_job_by_creation_key(creation_key=str(creation_key))
        if job is None:
            return not_found("Job not found")
        return Response({**import_job_payload(job), "job_id": job.id, "idempotent_replay": True})


class ImportDetailView(APIView):
    def get(self, _request: Request, job_id: str) -> Response:
        job = fetch_job(job_id)
        if job is None:
            return not_found("Job not found")
        return Response(import_detail_payload(job, fetch_items_for_job(job_id)))


class ImportCancelView(APIView):
    def post(self, _request: Request, job_id: str) -> Response:
        job = ImportService().cancel_job(job_id=job_id)
        if job is None:
            return not_found("Job not found")
        return Response(import_job_payload(job), status=status.HTTP_202_ACCEPTED)
