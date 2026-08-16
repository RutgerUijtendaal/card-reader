from __future__ import annotations

from pathlib import Path
import re
import shutil

from card_reader_core.config.settings import settings
from card_reader_core.storage import calculate_checksum

from .archive import DeveloperDataError, canonical_json_bytes, validate_archive
from .schema import PublishedBundle

_SAFE_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class InvalidDeveloperDataVersion(DeveloperDataError):
    pass


class PublishedBundleStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or settings.developer_data_root_dir).resolve()

    def publish(self, archive_path: Path) -> PublishedBundle:
        manifest, _payload = validate_archive(archive_path)
        version = self._validate_version(manifest.bundle_version)
        self.root.mkdir(parents=True, exist_ok=True)
        filename = f"card-reader-dev-data-{version}.tar.gz"
        target = self.root / filename
        metadata_path = self.root / f"{filename}.json"
        artifact = PublishedBundle(
            bundle_version=version,
            format_version=manifest.format_version,
            filename=filename,
            sha256=calculate_checksum(archive_path),
            size_bytes=archive_path.stat().st_size,
            created_at=manifest.created_at,
        )
        if target.exists() and metadata_path.exists():
            raise DeveloperDataError(f"Developer-data bundle {version} is already published.")
        if target.exists() or metadata_path.exists():
            return self._complete_interrupted_publish(
                archive_path=archive_path,
                target=target,
                metadata_path=metadata_path,
                artifact=artifact,
            )
        temp_target = self.root / f".{filename}.tmp"
        temp_metadata = self.root / f".{filename}.json.tmp"
        try:
            shutil.copy2(archive_path, temp_target)
            temp_metadata.write_bytes(canonical_json_bytes(artifact.model_dump(mode="json")))
            temp_target.replace(target)
            temp_metadata.replace(metadata_path)
        finally:
            temp_target.unlink(missing_ok=True)
            temp_metadata.unlink(missing_ok=True)
        self._write_current(artifact)
        return artifact

    def activate(self, artifact: PublishedBundle) -> None:
        self._write_current(artifact)

    def current(self) -> PublishedBundle | None:
        path = self.root / "current.json"
        if not path.is_file():
            return None
        try:
            artifact = PublishedBundle.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DeveloperDataError("Published developer-data metadata is invalid.") from exc
        return self.get(artifact.bundle_version)

    def get(self, bundle_version: str) -> PublishedBundle | None:
        version = self._validate_version(bundle_version)
        filename = f"card-reader-dev-data-{version}.tar.gz"
        metadata_path = self.root / f"{filename}.json"
        archive_path = self.root / filename
        if not metadata_path.is_file() or not archive_path.is_file():
            return None
        try:
            artifact = PublishedBundle.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DeveloperDataError(f"Published metadata for {version} is invalid.") from exc
        if artifact.filename != filename or artifact.bundle_version != version:
            raise DeveloperDataError(f"Published metadata for {version} does not match its filename.")
        if (
            archive_path.stat().st_size != artifact.size_bytes
            or calculate_checksum(archive_path) != artifact.sha256
        ):
            raise DeveloperDataError(f"Published developer-data bundle {version} failed integrity validation.")
        return artifact

    def archive_path(self, artifact: PublishedBundle) -> Path:
        return self.root / artifact.filename

    def _write_current(self, artifact: PublishedBundle) -> None:
        current_path = self.root / "current.json"
        temp_path = self.root / ".current.json.tmp"
        try:
            temp_path.write_bytes(canonical_json_bytes(artifact.model_dump(mode="json")))
            temp_path.replace(current_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def _complete_interrupted_publish(
        self,
        *,
        archive_path: Path,
        target: Path,
        metadata_path: Path,
        artifact: PublishedBundle,
    ) -> PublishedBundle:
        if target.exists():
            if (
                target.stat().st_size != artifact.size_bytes
                or calculate_checksum(target) != artifact.sha256
            ):
                raise DeveloperDataError(
                    f"Incomplete developer-data publication for {artifact.bundle_version} conflicts with the new archive."
                )
            temp_metadata = metadata_path.with_name(f".{metadata_path.name}.recovery.tmp")
            temp_metadata.write_bytes(canonical_json_bytes(artifact.model_dump(mode="json")))
            temp_metadata.replace(metadata_path)
        else:
            try:
                existing = PublishedBundle.model_validate_json(metadata_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise DeveloperDataError(
                    f"Incomplete metadata for {artifact.bundle_version} is invalid."
                ) from exc
            if existing != artifact:
                raise DeveloperDataError(
                    f"Incomplete developer-data publication for {artifact.bundle_version} conflicts with the new archive."
                )
            temp_target = target.with_name(f".{target.name}.recovery.tmp")
            shutil.copy2(archive_path, temp_target)
            temp_target.replace(target)
        self._write_current(artifact)
        return artifact

    @staticmethod
    def _validate_version(value: str) -> str:
        compact = value.strip()
        if not _SAFE_VERSION.fullmatch(compact):
            raise InvalidDeveloperDataVersion("Developer-data bundle version is invalid.")
        return compact
