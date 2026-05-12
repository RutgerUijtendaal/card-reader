from __future__ import annotations

from pathlib import Path, PurePosixPath

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


def forwards(apps, schema_editor) -> None:
    CardVersionImage = apps.get_model("card_reader_core", "CardVersionImage")
    for image in CardVersionImage.objects.only("id", "stored_path", "source_file").iterator():
        stored_path = _relativize_storage_path(image.stored_path, roots=("images",), default_root="images")
        source_file = _relativize_storage_path(
            image.source_file,
            roots=("uploads", "images", "maintenance"),
            default_root="uploads",
        )
        if image.stored_path == stored_path and image.source_file == source_file:
            continue
        CardVersionImage.objects.filter(id=image.id).update(stored_path=stored_path, source_file=source_file)


def backwards(apps, schema_editor) -> None:
    return None


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0009_convert_core_relations")]

    operations = [migrations.RunPython(forwards, backwards)]
