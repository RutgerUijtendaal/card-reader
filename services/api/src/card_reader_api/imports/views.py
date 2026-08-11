from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
from typing import cast

from django.core.files.uploadedfile import UploadedFile
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
from card_reader_core.repositories.import_jobs import (
    SUPPORTED_IMAGE_SUFFIXES,
    fetch_items_for_job,
    fetch_job,
    list_import_jobs,
)
from card_reader_core.models import CardPool, CardRole
from card_reader_core.services.imports import CardRoleMode, ImportCreationKeyConflict, ImportService
from card_reader_core.storage import build_storage_relative_path, resolve_storage_path

logger = logging.getLogger(__name__)


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
        serializer = ImportUploadSerializer(
            data={
                "creation_key": request.data.get("creation_key", ""),
                "template_id": request.data.get("template_id", ""),
                "content_version_base": request.data.get("content_version_base", ""),
                "content_version_description": request.data.get("content_version_description", ""),
                "options_json": request.data.get("options_json", "{}"),
                "files": request.FILES.getlist("files"),
                "card_pool": request.data.get("card_pool", ""),
                "card_role_mode": request.data.get("card_role_mode", "automatic"),
                "card_role_override": request.data.get("card_role_override", "[]"),
            }
        )
        if not serializer.is_valid():
            return serializer_error(serializer)

        fingerprint, uploads = _upload_fingerprint(
            template_id=serializer.validated_data["template_id"],
            content_version_base=serializer.validated_data["content_version_base"],
            content_version_description=serializer.validated_data["content_version_description"],
            options=serializer.validated_data["options_json"],
            card_pool=str(serializer.validated_data["card_pool"]),
            card_role_mode=str(serializer.validated_data["card_role_mode"]),
            card_role_override=serializer.validated_data["card_role_override"],
            files=serializer.validated_data["files"],
        )
        creation_key = str(serializer.validated_data["creation_key"])
        service = ImportService()
        existing = service.get_job_by_creation_key(creation_key=creation_key)
        if existing is not None:
            if existing.creation_fingerprint != fingerprint:
                return Response(
                    {"detail": "This creation key has already been used for a different import payload."},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(
                {**import_job_payload(existing), "job_id": existing.id, "idempotent_replay": True}
            )

        try:
            upload_dir = _save_supported_uploads(
                uploads,
                creation_key=creation_key,
                fingerprint=fingerprint,
            )
        except ImportCreationKeyConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        if upload_dir is None:
            return bad_request("No supported image files found in upload")

        try:
            job, idempotent_replay = service.create_job(
                source_path=str(upload_dir),
                template_id=serializer.validated_data["template_id"],
                options=serializer.validated_data["options_json"],
                content_version_base=serializer.validated_data["content_version_base"],
                content_version_description=serializer.validated_data["content_version_description"],
                creation_key=creation_key,
                creation_fingerprint=fingerprint,
                card_pool=cast(CardPool, serializer.validated_data["card_pool"]),
                card_role_mode=cast(CardRoleMode, serializer.validated_data["card_role_mode"]),
                card_role_override=cast(list[CardRole], serializer.validated_data["card_role_override"]),
            )
        except ImportCreationKeyConflict as exc:
            _discard_unclaimed_uploads(upload_dir)
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            _discard_unclaimed_uploads(upload_dir)
            return bad_request(str(exc))
        except Exception:
            logger.exception("Failed to create import job from upload. upload_dir=%s", upload_dir)
            return Response(
                {"detail": "Failed to create import job from upload. See API logs."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {**import_job_payload(job), "job_id": job.id, "idempotent_replay": idempotent_replay},
            status=status.HTTP_200_OK if idempotent_replay else status.HTTP_201_CREATED,
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


def _save_supported_uploads(
    files: list[tuple[UploadedFile, str]],
    *,
    creation_key: str,
    fingerprint: str,
) -> str | None:
    upload_dir = build_storage_relative_path("uploads", creation_key, fingerprint)
    resolve_storage_path(upload_dir).mkdir(parents=True, exist_ok=True)
    saved_count = 0

    for index, (upload, expected_checksum) in enumerate(files):
        original_name = Path(upload.name or f"upload-{index}.img").name
        if Path(original_name).suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            continue
        target_file = resolve_storage_path(
            build_storage_relative_path(upload_dir, f"{index:04d}-{original_name}")
        )
        if target_file.is_file():
            if _sha256_path(target_file) != expected_checksum:
                raise ImportCreationKeyConflict(
                    "Stored upload content conflicts with this creation key."
                )
        else:
            _publish_upload_atomically(
                upload,
                target_file=target_file,
                expected_checksum=expected_checksum,
            )
        saved_count += 1

    return upload_dir if saved_count else None


def _discard_unclaimed_uploads(upload_dir: str) -> None:
    try:
        shutil.rmtree(resolve_storage_path(upload_dir))
    except FileNotFoundError:
        return
    except OSError:
        logger.warning(
            "Failed to remove unclaimed import uploads. upload_dir=%s",
            upload_dir,
            exc_info=True,
        )


def _publish_upload_atomically(
    upload: UploadedFile,
    *,
    target_file: Path,
    expected_checksum: str,
) -> None:
    staged_file = target_file.with_name(f".{target_file.name}.{os.urandom(16).hex()}.tmp")
    try:
        digest = hashlib.sha256()
        with staged_file.open("xb") as stream:
            for chunk in upload.chunks():
                stream.write(chunk)
                digest.update(chunk)
            stream.flush()
            os.fsync(stream.fileno())

        if digest.hexdigest() != expected_checksum:
            raise ImportCreationKeyConflict("Upload content changed while it was being stored.")

        try:
            os.link(staged_file, target_file)
        except FileExistsError:
            if _sha256_path(target_file) != expected_checksum:
                raise ImportCreationKeyConflict(
                    "Stored upload content conflicts with this creation key."
                ) from None
    finally:
        staged_file.unlink(missing_ok=True)


def _upload_fingerprint(
    *,
    template_id: str,
    content_version_base: str,
    content_version_description: str,
    options: dict[str, object],
    card_pool: str,
    card_role_mode: str,
    card_role_override: list[str],
    files: list[UploadedFile],
) -> tuple[str, list[tuple[UploadedFile, str]]]:
    file_records: list[dict[str, object]] = []
    uploads: list[tuple[UploadedFile, str]] = []
    for upload in files:
        digest = hashlib.sha256()
        for chunk in upload.chunks():
            digest.update(chunk)
        upload.seek(0)
        checksum = digest.hexdigest()
        file_records.append(
            {"name": Path(upload.name or "upload.img").name, "size": upload.size, "sha256": checksum}
        )
        uploads.append((upload, checksum))
    payload = {
        "template_id": template_id,
        "content_version_base": content_version_base,
        "content_version_description": content_version_description,
        "options": options,
        "card_pool": card_pool,
        "card_role_mode": card_role_mode,
        "card_role_override": card_role_override,
        "files": file_records,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), uploads


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
