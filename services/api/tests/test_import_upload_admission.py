from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from card_reader_api.imports.creation import (
    ImportAdmissionConflict,
    ImportAdmissionRejected,
    ImportAdmissionUncertain,
    ImportUploadAdmission,
    StagedImportUpload,
    _upload_fingerprint,
)
from card_reader_core.imports import ImportJobInputValidationError
from card_reader_core.models import ContentVersion, ImportJob
from card_reader_core.services.imports import (
    ImportCreationKeyConflict,
    ImportCreationRejected,
    ImportService,
)
import card_reader_core.services.imports.service as import_service_module
from card_reader_core.storage import build_storage_relative_path, resolve_storage_path


def _validated_data(*, creation_key: str | None = None) -> dict[str, object]:
    return {
        "creation_key": creation_key or str(uuid4()),
        "template_id": "mtg-like-v1",
        "content_version_base": "14.1",
        "content_version_description": "Admission test.",
        "options_json": {},
        "files": [SimpleUploadedFile("card.png", b"image", content_type="image/png")],
        "card_pool": "player",
        "card_role_mode": "automatic",
        "card_role_override": [],
    }


class _FakeImportService:
    def __init__(self) -> None:
        self.existing: object | None = None
        self.create_error: Exception | None = None
        self.lookup_error_after_create: Exception | None = None
        self.create_called = False

    def prevalidate_job_creation(self, **_kwargs: object) -> None:
        return

    def get_job_by_creation_key(self, *, creation_key: str) -> object | None:
        del creation_key
        if self.create_called and self.lookup_error_after_create is not None:
            raise self.lookup_error_after_create
        return self.existing

    def create_job(self, **kwargs: object) -> object:
        self.create_called = True
        if self.create_error is not None:
            raise self.create_error
        raise AssertionError(f"Unexpected create call: {kwargs}")


def test_prevalidation_rejection_happens_before_upload_staging() -> None:
    data = _validated_data()
    creation_key = str(data["creation_key"])
    service = _FakeImportService()

    def reject(**_kwargs: object) -> None:
        raise ImportCreationRejected("Unknown template_id 'missing'")

    service.prevalidate_job_creation = reject  # type: ignore[method-assign]

    with pytest.raises(ImportAdmissionRejected, match="Unknown template_id"):
        ImportUploadAdmission(service=service).admit(data)  # type: ignore[arg-type]

    creation_dir = resolve_storage_path(build_storage_relative_path("uploads", creation_key))
    assert not creation_dir.exists() or list(creation_dir.iterdir()) == []


def test_prevalidation_rejection_discards_a_preserved_exact_retry_stage() -> None:
    data = _validated_data()
    creation_key = str(data["creation_key"])
    fingerprint, uploads = _upload_fingerprint(
        template_id=str(data["template_id"]),
        content_version_base=str(data["content_version_base"]),
        content_version_description=str(data["content_version_description"]),
        options={},
        card_pool="player",
        card_role_mode="automatic",
        card_role_override=[],
        files=data["files"],  # type: ignore[arg-type]
    )
    staged = StagedImportUpload.publish(
        uploads,
        creation_key=creation_key,
        fingerprint=fingerprint,
    )
    assert staged._validated_directory().is_dir()
    service = _FakeImportService()

    def reject(**_kwargs: object) -> None:
        raise ImportCreationRejected("Unknown template_id 'missing'")

    service.prevalidate_job_creation = reject  # type: ignore[method-assign]

    with pytest.raises(ImportAdmissionRejected, match="Unknown template_id"):
        ImportUploadAdmission(service=service).admit(data)  # type: ignore[arg-type]

    creation_dir = resolve_storage_path(build_storage_relative_path("uploads", creation_key))
    assert not creation_dir.exists() or list(creation_dir.iterdir()) == []


def test_retry_cleanup_failure_does_not_replace_prevalidation_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = _validated_data()
    service = _FakeImportService()

    def reject(**_kwargs: object) -> None:
        raise ImportCreationRejected("Unknown template_id 'missing'")

    service.prevalidate_job_creation = reject  # type: ignore[method-assign]
    monkeypatch.setattr(
        StagedImportUpload,
        "reconcile_existing",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("unreadable stage")),
    )

    with pytest.raises(ImportAdmissionRejected, match="Unknown template_id"):
        ImportUploadAdmission(service=service).admit(data)  # type: ignore[arg-type]


def test_definitive_creation_rejection_discards_only_the_owned_stage() -> None:
    data = _validated_data()
    creation_key = str(data["creation_key"])
    service = _FakeImportService()
    service.create_error = ImportCreationRejected("Rejected after staging")

    with pytest.raises(ImportAdmissionRejected, match="Rejected after staging"):
        ImportUploadAdmission(service=service).admit(data)  # type: ignore[arg-type]

    creation_dir = resolve_storage_path(build_storage_relative_path("uploads", creation_key))
    assert not creation_dir.exists() or list(creation_dir.iterdir()) == []


def test_post_staging_rejection_discards_a_preserved_exact_retry_stage() -> None:
    data = _validated_data()
    creation_key = str(data["creation_key"])
    fingerprint, uploads = _upload_fingerprint(
        template_id=str(data["template_id"]),
        content_version_base=str(data["content_version_base"]),
        content_version_description=str(data["content_version_description"]),
        options={},
        card_pool="player",
        card_role_mode="automatic",
        card_role_override=[],
        files=data["files"],  # type: ignore[arg-type]
    )
    StagedImportUpload.publish(
        uploads,
        creation_key=creation_key,
        fingerprint=fingerprint,
    )
    service = _FakeImportService()
    service.create_error = ImportCreationRejected("Template disappeared after staging")

    with pytest.raises(ImportAdmissionRejected, match="Template disappeared after staging"):
        ImportUploadAdmission(service=service).admit(data)  # type: ignore[arg-type]

    creation_dir = resolve_storage_path(build_storage_relative_path("uploads", creation_key))
    assert not creation_dir.exists() or list(creation_dir.iterdir()) == []


def test_unknown_ownership_preserves_the_isolated_stage_for_reconciliation() -> None:
    data = _validated_data()
    creation_key = str(data["creation_key"])
    service = _FakeImportService()
    service.create_error = RuntimeError("database response lost")
    service.lookup_error_after_create = RuntimeError("lookup unavailable")

    with pytest.raises(ImportAdmissionUncertain, match="See API logs"):
        ImportUploadAdmission(service=service).admit(data)  # type: ignore[arg-type]

    creation_dir = resolve_storage_path(build_storage_relative_path("uploads", creation_key))
    fingerprint_dirs = list(creation_dir.iterdir())
    assert len(fingerprint_dirs) == 1
    assert [path.name for path in fingerprint_dirs[0].iterdir()] == ["0000-card.png"]


def test_cleanup_failure_does_not_replace_the_domain_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _FakeImportService()
    service.create_error = ImportCreationKeyConflict("Creation key conflict")
    monkeypatch.setattr(StagedImportUpload, "discard", lambda _self: False)

    with pytest.raises(ImportAdmissionConflict, match="Creation key conflict"):
        ImportUploadAdmission(service=service).admit(_validated_data())  # type: ignore[arg-type]


def test_staging_conflict_is_translated_to_an_admission_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def conflict(*_args: object, **_kwargs: object) -> StagedImportUpload:
        raise ImportCreationKeyConflict("Stored upload content conflicts")

    monkeypatch.setattr(StagedImportUpload, "publish", conflict)

    with pytest.raises(ImportAdmissionConflict, match="Stored upload content conflicts"):
        ImportUploadAdmission(service=_FakeImportService()).admit(  # type: ignore[arg-type]
            _validated_data()
        )


def test_matching_replay_returns_before_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = _validated_data()
    fingerprint, _uploads = _upload_fingerprint(
        template_id=str(data["template_id"]),
        content_version_base=str(data["content_version_base"]),
        content_version_description=str(data["content_version_description"]),
        options={},
        card_pool="player",
        card_role_mode="automatic",
        card_role_override=[],
        files=data["files"],  # type: ignore[arg-type]
    )
    service = _FakeImportService()
    service.existing = SimpleNamespace(id="existing", creation_fingerprint=fingerprint)
    service.prevalidate_job_creation = lambda **_kwargs: pytest.fail(  # type: ignore[method-assign]
        "matching replay must return before current domain prevalidation"
    )
    monkeypatch.setattr(
        StagedImportUpload,
        "publish",
        lambda *_args, **_kwargs: pytest.fail("matching replay must not stage files"),
    )

    result = ImportUploadAdmission(service=service).admit(data)  # type: ignore[arg-type]

    assert result.idempotent_replay is True
    assert result.job.id == "existing"


def test_creation_key_conflict_discards_a_preserved_losing_fingerprint() -> None:
    data = _validated_data()
    creation_key = str(data["creation_key"])
    fingerprint, uploads = _upload_fingerprint(
        template_id=str(data["template_id"]),
        content_version_base=str(data["content_version_base"]),
        content_version_description=str(data["content_version_description"]),
        options={},
        card_pool="player",
        card_role_mode="automatic",
        card_role_override=[],
        files=data["files"],  # type: ignore[arg-type]
    )
    StagedImportUpload.publish(
        uploads,
        creation_key=creation_key,
        fingerprint=fingerprint,
    )
    service = _FakeImportService()
    service.existing = SimpleNamespace(id="winner", creation_fingerprint="b" * 64)

    with pytest.raises(ImportAdmissionConflict, match="different import payload"):
        ImportUploadAdmission(service=service).admit(data)  # type: ignore[arg-type]

    creation_dir = resolve_storage_path(build_storage_relative_path("uploads", creation_key))
    assert not creation_dir.exists() or list(creation_dir.iterdir()) == []


def test_staged_upload_rejects_cleanup_paths_outside_exact_fingerprint_directory() -> None:
    creation_key = str(uuid4())
    staged = StagedImportUpload(
        creation_key=creation_key,
        fingerprint="a" * 64,
        relative_path=build_storage_relative_path("uploads", creation_key),
        owned_files=(Path("unexpected"),),
    )

    with pytest.raises(ValueError, match="Invalid staged import directory"):
        staged.discard()


def test_core_creation_rolls_back_content_version_when_job_creation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_job_creation(**_kwargs: object) -> object:
        raise RuntimeError("item creation failed")

    monkeypatch.setattr(import_service_module, "create_import_job", fail_job_creation)
    content_version_count = ContentVersion.objects.count()

    with pytest.raises(RuntimeError, match="item creation failed"):
        ImportService().create_job(
            source_path="uploads/test/source",
            template_id="mtg-like-v1",
            options={},
            content_version_base="14.1",
            content_version_description="Atomic creation.",
            creation_key=str(uuid4()),
            creation_fingerprint="a" * 64,
            card_pool="player",
        )

    assert ContentVersion.objects.count() == content_version_count
    assert not ImportJob.objects.exists()


def test_core_creation_converts_authoritative_input_validation_to_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_job_creation(**_kwargs: object) -> object:
        raise ImportJobInputValidationError("Unknown template_id 'deleted'")

    monkeypatch.setattr(import_service_module, "create_import_job", reject_job_creation)
    content_version_count = ContentVersion.objects.count()

    with pytest.raises(ImportCreationRejected, match="Unknown template_id 'deleted'"):
        ImportService().create_job(
            source_path="uploads/test/source",
            template_id="mtg-like-v1",
            options={},
            content_version_base="14.1",
            content_version_description="Late validation.",
            creation_key=str(uuid4()),
            creation_fingerprint="a" * 64,
            card_pool="player",
        )

    assert ContentVersion.objects.count() == content_version_count
    assert not ImportJob.objects.exists()
