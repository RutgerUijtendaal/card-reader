from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from card_reader_core.models import CardVersionImage, now_utc
from card_reader_core.storage import (
    build_storage_relative_path,
    convert_image_to_webp,
    resolve_storage_path,
)


@dataclass(slots=True)
class CardImageConversionFailure:
    image_id: str
    path: str
    detail: str


@dataclass(slots=True)
class CardImageConversionResult:
    converted: int = 0
    already_webp: int = 0
    missing: int = 0
    failed: int = 0
    bytes_before: int = 0
    bytes_after: int = 0
    failures: list[CardImageConversionFailure] = field(default_factory=list)

    @property
    def message(self) -> str:
        saved_bytes = max(self.bytes_before - self.bytes_after, 0)
        return (
            f"Converted {self.converted} card image{'s' if self.converted != 1 else ''} "
            f"to WebP. {self.already_webp} already WebP, {self.missing} missing, "
            f"{self.failed} failed. Saved {format_byte_count(saved_bytes)}."
        )


def convert_card_images_to_webp() -> CardImageConversionResult:
    result = CardImageConversionResult()
    images = CardVersionImage.objects.order_by("id").only("id", "source_file", "stored_path", "checksum")
    for image in images.iterator():
        _convert_card_image(image, result)
    return result


def format_byte_count(value: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{int(size)} B"


def _convert_card_image(image: CardVersionImage, result: CardImageConversionResult) -> None:
    stored_path = resolve_storage_path(image.stored_path)
    readable_path = stored_path
    if not stored_path.exists() or not stored_path.is_file():
        source_path = resolve_storage_path(image.source_file)
        if not source_path.exists() or not source_path.is_file():
            result.missing += 1
            return
        readable_path = source_path

    original_size = readable_path.stat().st_size
    if readable_path.suffix.lower() == ".webp":
        try:
            _verify_readable_image(readable_path)
            if readable_path != stored_path:
                CardVersionImage.objects.filter(id=image.id).update(
                    stored_path=image.source_file,
                    updated_at=now_utc(),
                )
            result.already_webp += 1
            result.bytes_before += original_size
            result.bytes_after += original_size
        except Exception as exc:
            _record_failure(image, result, exc)
        return

    target_relative_path = build_storage_relative_path("images", f"{image.checksum}.webp")
    target_path = resolve_storage_path(target_relative_path)

    try:
        if target_path.exists():
            _verify_readable_image(target_path)
        else:
            convert_image_to_webp(readable_path, target_path)
            _verify_readable_image(target_path)
        target_size = target_path.stat().st_size
        CardVersionImage.objects.filter(id=image.id).update(
            stored_path=target_relative_path,
            updated_at=now_utc(),
        )
        result.converted += 1
        result.bytes_before += original_size
        result.bytes_after += target_size
    except Exception as exc:
        _record_failure(image, result, exc)


def _record_failure(
    image: CardVersionImage,
    result: CardImageConversionResult,
    exc: Exception,
) -> None:
    result.failed += 1
    result.failures.append(
        CardImageConversionFailure(
            image_id=image.id,
            path=Path(image.stored_path).as_posix(),
            detail=str(exc),
        )
    )


def _verify_readable_image(path: Path) -> None:
    with Image.open(path) as image:
        image.verify()
