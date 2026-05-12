from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from django.db import migrations


def _looks_absolute_path(value: str) -> bool:
    if not value:
        return False
    if value.startswith(("/", "\\")):
        return True
    return len(value) >= 3 and value[1] == ":" and value[2] in {"\\", "/"}


def _normalize_relative_storage_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part and part != "."]
    return PurePosixPath(*parts).as_posix()


def _relativize_storage_path(value: str, *, roots: tuple[str, ...], default_root: str | None = None) -> str:
    if not _looks_absolute_path(value):
        return _normalize_relative_storage_path(value)

    try:
        from card_reader_core.settings import settings

        return Path(value).relative_to(settings.storage_root_dir).as_posix()
    except Exception:
        pass

    normalized = value.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part and part != "."]
    indexes = [index for index, part in enumerate(parts) if part.lower() in {root.lower() for root in roots}]
    if indexes:
        return PurePosixPath(*parts[indexes[-1] :]).as_posix()
    if default_root is not None and parts:
        return PurePosixPath(default_root, parts[-1]).as_posix()
    return PurePosixPath(*parts).as_posix()


def forwards(apps: Any, schema_editor: Any) -> None:
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")

    for job in ImportJob.objects.only("id", "source_path").iterator():
        relative_path = _relativize_storage_path(
            job.source_path,
            roots=("uploads", "maintenance", "images"),
            default_root="uploads",
        )
        if job.source_path == relative_path:
            continue
        ImportJob.objects.filter(id=job.id).update(source_path=relative_path)

    for item in ImportJobItem.objects.only("id", "source_file").iterator():
        relative_path = _relativize_storage_path(
            item.source_file,
            roots=("uploads", "images", "maintenance"),
            default_root="uploads",
        )
        if item.source_file == relative_path:
            continue
        ImportJobItem.objects.filter(id=item.id).update(source_file=relative_path)


def backwards(apps: Any, schema_editor: Any) -> None:
    return None


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0010_relativize_card_image_paths")]

    operations = [migrations.RunPython(forwards, backwards)]
