from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from django.core.files.uploadedfile import UploadedFile
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from card_reader_api.imports.serializers import ImportUploadSerializer, import_detail_payload, import_job_payload
from card_reader_core.repositories.import_jobs_repository import (
    SUPPORTED_IMAGE_SUFFIXES,
    fetch_items_for_job,
    fetch_job,
    list_import_jobs,
)
from card_reader_core.services.imports import ImportService
from card_reader_core.storage import build_storage_relative_path, resolve_storage_path

logger = logging.getLogger(__name__)


class ImportListView(APIView):
    def get(self, _request: Request) -> Response:
        jobs = list_import_jobs()
        return Response([import_job_payload(job) for job in jobs])


class ImportUploadView(APIView):
    def post(self, request: Request) -> Response:
        serializer = ImportUploadSerializer(
            data={
                "template_id": request.data.get("template_id", ""),
                "options_json": request.data.get("options_json", "{}"),
                "files": request.FILES.getlist("files"),
            }
        )
        if not serializer.is_valid():
            return _serializer_error(serializer)

        upload_dir = _save_supported_uploads(serializer.validated_data["files"])
        if upload_dir is None:
            return _bad_request("No supported image files found in upload")

        try:
            job = ImportService().create_job(
                source_path=str(upload_dir),
                template_id=serializer.validated_data["template_id"],
                options=serializer.validated_data["options_json"],
            )
        except ValueError as exc:
            return _bad_request(str(exc))
        except Exception:
            logger.exception("Failed to create import job from upload. upload_dir=%s", upload_dir)
            return Response(
                {"detail": "Failed to create import job from upload. See API logs."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(import_job_payload(job), status=status.HTTP_201_CREATED)


class ImportDetailView(APIView):
    def get(self, _request: Request, job_id: str) -> Response:
        job = fetch_job(job_id)
        if job is None:
            return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(import_detail_payload(job, fetch_items_for_job(job_id)))


class ImportCancelView(APIView):
    def post(self, _request: Request, job_id: str) -> Response:
        job = ImportService().cancel_job(job_id=job_id)
        if job is None:
            return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(import_job_payload(job), status=status.HTTP_202_ACCEPTED)


def _save_supported_uploads(files: list[UploadedFile]) -> str | None:
    upload_dir = build_storage_relative_path("uploads", str(uuid4()))
    resolve_storage_path(upload_dir).mkdir(parents=True, exist_ok=True)
    saved_count = 0

    for index, upload in enumerate(files):
        original_name = Path(upload.name or f"upload-{index}.img").name
        if Path(original_name).suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            continue
        target_file = resolve_storage_path(
            build_storage_relative_path(upload_dir, f"{index:04d}-{original_name}")
        )
        with target_file.open("wb") as stream:
            for chunk in upload.chunks():
                stream.write(chunk)
        saved_count += 1

    return upload_dir if saved_count else None


def _bad_request(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _serializer_error(serializer: BaseSerializer[Any]) -> Response:
    errors = serializer.errors
    detail = next(iter(cast(Mapping[str, object], errors).values()), "Invalid request.")
    if isinstance(detail, list):
        detail = detail[0]
    return Response({"detail": str(detail)}, status=status.HTTP_400_BAD_REQUEST)
