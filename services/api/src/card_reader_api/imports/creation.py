from __future__ import annotations

from dataclasses import dataclass
import errno
import hashlib
import json
import logging
import os
from pathlib import Path, PurePosixPath
from collections.abc import Sequence
from typing import cast
from uuid import UUID

from django.core.files.uploadedfile import UploadedFile

from card_reader_core.imports import SUPPORTED_IMAGE_SUFFIXES
from card_reader_core.models import CardPool, CardRole, ImportJob
from card_reader_core.services.imports import (
    CardRoleMode,
    ImportCreationKeyConflict,
    ImportCreationRejected,
    ImportService,
)
from card_reader_core.storage import build_storage_relative_path, resolve_storage_path

logger = logging.getLogger(__name__)


class ImportAdmissionConflict(ValueError):
    pass


class ImportAdmissionRejected(ValueError):
    pass


class ImportAdmissionUncertain(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportAdmissionResult:
    job: ImportJob
    idempotent_replay: bool


@dataclass
class StagedImportUpload:
    creation_key: str
    fingerprint: str
    relative_path: str
    claimed: bool = False
    owned_files: tuple[Path, ...] = ()

    @classmethod
    def publish(
        cls,
        uploads: list[tuple[UploadedFile, str]],
        *,
        creation_key: str,
        fingerprint: str,
    ) -> StagedImportUpload:
        relative_path = build_storage_relative_path("uploads", creation_key, fingerprint)
        staged = cls(
            creation_key=creation_key,
            fingerprint=fingerprint,
            relative_path=relative_path,
        )
        target_dir = staged._validated_directory()
        target_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0
        owned_files: list[Path] = []
        try:
            for index, (upload, expected_checksum) in enumerate(uploads):
                original_name = Path(upload.name or f"upload-{index}.img").name
                if Path(original_name).suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
                    continue
                target_file = target_dir / f"{index:04d}-{original_name}"
                if target_file.is_file():
                    if _sha256_path(target_file) != expected_checksum:
                        raise ImportCreationKeyConflict(
                            "Stored upload content conflicts with this creation key."
                        )
                else:
                    created = _publish_upload_atomically(
                        upload,
                        target_file=target_file,
                        expected_checksum=expected_checksum,
                    )
                    if created:
                        owned_files.append(target_file)
                saved_count += 1
        except Exception:
            staged.owned_files = tuple(owned_files)
            staged.discard()
            raise
        staged.owned_files = tuple(owned_files)
        if saved_count == 0:
            staged.discard()
            raise ImportAdmissionRejected("No supported image files found in upload")
        return staged

    @classmethod
    def reconcile_existing(
        cls,
        uploads: list[tuple[UploadedFile, str]],
        *,
        creation_key: str,
        fingerprint: str,
    ) -> StagedImportUpload:
        relative_path = build_storage_relative_path("uploads", creation_key, fingerprint)
        staged = cls(
            creation_key=creation_key,
            fingerprint=fingerprint,
            relative_path=relative_path,
        )
        target_dir = staged._validated_directory()
        cleanup_files: list[Path] = []
        for index, (upload, expected_checksum) in enumerate(uploads):
            original_name = Path(upload.name or f"upload-{index}.img").name
            if Path(original_name).suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
                continue
            target_file = target_dir / f"{index:04d}-{original_name}"
            if target_file.is_file() and _sha256_path(target_file) == expected_checksum:
                cleanup_files.append(target_file)
        staged.owned_files = tuple(cleanup_files)
        return staged

    def claim(self) -> None:
        self.claimed = True

    def discard(self) -> bool:
        if self.claimed:
            return False
        try:
            directory = self._validated_directory()
            for path in self.owned_files:
                if path.parent != directory:
                    raise ValueError("Invalid staged import file path.")
                path.unlink(missing_ok=True)
            directory.rmdir()
        except FileNotFoundError:
            pass
        except OSError as exc:
            if getattr(exc, "winerror", None) == 145 or exc.errno in {
                errno.ENOTEMPTY,
                errno.EEXIST,
            }:
                return True
            logger.warning(
                "Failed to remove unclaimed import uploads. upload_dir=%s",
                self.relative_path,
                exc_info=True,
            )
            return False
        return True

    def _validated_directory(self) -> Path:
        parts = PurePosixPath(self.relative_path).parts
        if parts != ("uploads", self.creation_key, self.fingerprint):
            raise ValueError("Invalid staged import directory.")
        if str(UUID(self.creation_key)) != self.creation_key:
            raise ValueError("Invalid staged import creation key.")
        if len(self.fingerprint) != 64 or any(char not in "0123456789abcdef" for char in self.fingerprint):
            raise ValueError("Invalid staged import fingerprint.")
        return resolve_storage_path(self.relative_path)


class ImportUploadAdmission:
    def __init__(self, service: ImportService | None = None) -> None:
        self._service = service or ImportService()

    def admit(self, validated_data: dict[str, object]) -> ImportAdmissionResult:
        creation_key = str(validated_data["creation_key"])
        template_id = str(validated_data["template_id"])
        content_version_base = str(validated_data["content_version_base"])
        card_pool = cast(CardPool, validated_data["card_pool"])
        card_role_mode = cast(CardRoleMode, validated_data["card_role_mode"])
        card_role_override = cast(list[CardRole], validated_data["card_role_override"])
        fingerprint, uploads = _upload_fingerprint(
            template_id=template_id,
            content_version_base=content_version_base,
            content_version_description=str(validated_data["content_version_description"]),
            options=cast(dict[str, object], validated_data["options_json"]),
            card_pool=card_pool,
            card_role_mode=card_role_mode,
            card_role_override=card_role_override,
            files=cast(list[UploadedFile], validated_data["files"]),
        )
        existing = self._service.get_job_by_creation_key(creation_key=creation_key)
        if existing is not None:
            if existing.creation_fingerprint != fingerprint:
                raise ImportAdmissionConflict(
                    "This creation key has already been used for a different import payload."
                )
            return ImportAdmissionResult(job=existing, idempotent_replay=True)

        try:
            self._service.prevalidate_job_creation(
                template_id=template_id,
                content_version_base=content_version_base,
                content_version_description=str(validated_data["content_version_description"]),
                card_pool=card_pool,
                card_role_mode=card_role_mode,
                card_role_override=card_role_override,
            )
        except ImportCreationRejected as exc:
            return self._reconcile_prevalidation_rejection(
                creation_key=creation_key,
                fingerprint=fingerprint,
                uploads=uploads,
                error=exc,
            )

        staged = StagedImportUpload.publish(
            uploads,
            creation_key=creation_key,
            fingerprint=fingerprint,
        )
        try:
            result = self._service.create_job(
                source_path=staged.relative_path,
                template_id=template_id,
                options=cast(dict[str, object], validated_data["options_json"]),
                content_version_base=content_version_base,
                content_version_description=str(validated_data["content_version_description"]),
                creation_key=creation_key,
                creation_fingerprint=fingerprint,
                card_pool=card_pool,
                card_role_mode=card_role_mode,
                card_role_override=card_role_override,
            )
        except ImportCreationKeyConflict as exc:
            staged.discard()
            raise ImportAdmissionConflict(str(exc)) from exc
        except ImportCreationRejected as exc:
            staged.discard()
            raise ImportAdmissionRejected(str(exc)) from exc
        except Exception as exc:
            return self._reconcile_uncertain_stage(
                staged=staged,
                fingerprint=fingerprint,
                error=exc,
            )

        staged.claim()
        return ImportAdmissionResult(
            job=result.job,
            idempotent_replay=result.idempotent_replay,
        )

    def _reconcile_prevalidation_rejection(
        self,
        *,
        creation_key: str,
        fingerprint: str,
        uploads: list[tuple[UploadedFile, str]],
        error: ImportCreationRejected,
    ) -> ImportAdmissionResult:
        try:
            existing = self._service.get_job_by_creation_key(creation_key=creation_key)
        except Exception:
            logger.exception(
                "Import ownership lookup failed after validation rejection; preserving isolated "
                "stage. creation_key=%s fingerprint=%s",
                creation_key,
                fingerprint,
            )
            raise ImportAdmissionUncertain(
                "Failed to reconcile rejected import upload. See API logs."
            ) from error
        if existing is not None:
            if existing.creation_fingerprint != fingerprint:
                raise ImportAdmissionConflict(
                    "This creation key has already been used for a different import payload."
                ) from error
            return ImportAdmissionResult(job=existing, idempotent_replay=True)

        StagedImportUpload.reconcile_existing(
            uploads,
            creation_key=creation_key,
            fingerprint=fingerprint,
        ).discard()
        raise ImportAdmissionRejected(str(error)) from error

    def _reconcile_uncertain_stage(
        self,
        *,
        staged: StagedImportUpload,
        fingerprint: str,
        error: Exception,
    ) -> ImportAdmissionResult:
        try:
            existing = self._service.get_job_by_creation_key(creation_key=staged.creation_key)
        except Exception:
            logger.exception(
                "Import ownership lookup failed; preserving isolated stage. upload_dir=%s",
                staged.relative_path,
            )
            raise ImportAdmissionUncertain(
                "Failed to create import job from upload. See API logs."
            ) from error
        if existing is not None:
            if existing.creation_fingerprint != fingerprint:
                staged.discard()
                raise ImportAdmissionConflict(
                    "This creation key has already been used for a different import payload."
                ) from error
            staged.claim()
            logger.warning(
                "Recovered committed import after an unexpected creation error. job_id=%s",
                existing.id,
                exc_info=error,
            )
            return ImportAdmissionResult(job=existing, idempotent_replay=True)

        logger.exception(
            "Import ownership remains uncertain; preserving isolated stage. upload_dir=%s",
            staged.relative_path,
            exc_info=error,
        )
        raise ImportAdmissionUncertain(
            "Failed to create import job from upload. See API logs."
        ) from error


def _publish_upload_atomically(
    upload: UploadedFile,
    *,
    target_file: Path,
    expected_checksum: str,
) -> bool:
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
            return False
        return True
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
    card_role_override: Sequence[str],
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
        "card_role_override": list(card_role_override),
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
