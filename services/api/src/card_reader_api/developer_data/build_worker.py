from __future__ import annotations

import logging
import os
from pathlib import Path
import tempfile

from card_reader_core.config.settings import settings
from card_reader_core.models import DeveloperDataBuild
from card_reader_core.operations.developer_data import (
    DeveloperDataError,
    PublishedBundleStore,
    export_developer_data,
    sha256_file,
)
from card_reader_core.operations.developer_data.schema import PublishedBundle
from card_reader_core.repositories.developer_data import (
    mark_build_failed,
    mark_build_succeeded,
)

from .validation import validate_temporary_import

logger = logging.getLogger(__name__)


def process_developer_data_build(build: DeveloperDataBuild) -> None:
    try:
        store = PublishedBundleStore()
        artifact = store.get(build.bundle_version)
        if artifact is None:
            artifact = _export_validate_publish(build)
        else:
            store.activate(artifact)
        mark_build_succeeded(build_id=build.id, artifact=artifact)
        logger.info(
            "Developer-data build published. build_id=%s bundle_version=%s",
            build.id,
            build.bundle_version,
        )
    except Exception as exc:
        logger.exception(
            "Developer-data build failed. build_id=%s bundle_version=%s",
            build.id,
            build.bundle_version,
        )
        mark_build_failed(build_id=build.id, error_message=_public_error_message(exc))


def _export_validate_publish(build: DeveloperDataBuild) -> PublishedBundle:
    selection_path = settings.developer_data_selection_path.resolve()
    if not selection_path.is_file():
        raise DeveloperDataError("The deployed developer-data selection file is unavailable.")
    with tempfile.TemporaryDirectory(prefix="card-reader-dev-data-build-") as temp_value:
        archive_path = Path(temp_value) / f"card-reader-dev-data-{build.bundle_version}.tar.gz"
        manifest = export_developer_data(
            selection_path=selection_path,
            output_path=archive_path,
            source_revision=os.getenv("CARD_READER_RELEASE_REVISION", "unknown"),
            bundle_version=build.bundle_version,
        )
        archive_sha256 = sha256_file(archive_path)
        validate_temporary_import(
            archive_path=archive_path,
            bundle_version=manifest.bundle_version,
            archive_sha256=archive_sha256,
        )
        return _publish_or_adopt_existing(
            store=PublishedBundleStore(),
            archive_path=archive_path,
            bundle_version=build.bundle_version,
        )


def _publish_or_adopt_existing(
    *,
    store: PublishedBundleStore,
    archive_path: Path,
    bundle_version: str,
) -> PublishedBundle:
    try:
        return store.publish(archive_path)
    except DeveloperDataError:
        artifact = store.get(bundle_version)
        if artifact is None:
            raise
        store.activate(artifact)
        return artifact


def _public_error_message(exc: Exception) -> str:
    if isinstance(exc, DeveloperDataError):
        return str(exc)
    return "The build failed unexpectedly. Check the developer-data worker logs."
