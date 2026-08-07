from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
from dataclasses import dataclass

from PIL import Image, ImageOps

from card_reader_core.config.settings import settings
from card_reader_core.models import TtsCardSheet
from card_reader_core.repositories.tts_card_sheets import (
    get_sheet_with_slots,
    mark_render_failed,
    mark_render_succeeded,
)
from card_reader_core.storage import resolve_storage_path

_BACKGROUND = (0, 0, 0)


@dataclass(frozen=True)
class TtsCardSheetLayout:
    version: int
    columns: int
    rows: int
    cell_width: int
    cell_height: int

    @property
    def image_size(self) -> tuple[int, int]:
        return self.columns * self.cell_width, self.rows * self.cell_height


_LAYOUTS = {
    1: TtsCardSheetLayout(
        version=1,
        columns=10,
        rows=7,
        cell_width=400,
        cell_height=560,
    )
}


class TtsCardSheetRenderError(RuntimeError):
    pass


def tts_card_sheet_path(sheet_id: str, rendered_checksum: str) -> Path:
    return settings.tts_card_sheets_dir / f"{sheet_id}.{rendered_checksum}.webp"


def get_tts_card_sheet_layout(version: int) -> TtsCardSheetLayout:
    layout = _LAYOUTS.get(version)
    if layout is None:
        raise TtsCardSheetRenderError(f"Unsupported TTS card sheet layout version {version}.")
    return layout


def render_claimed_sheet(claimed_sheet: TtsCardSheet) -> TtsCardSheet:
    sheet = get_sheet_with_slots(str(claimed_sheet.id))
    if sheet is None:
        raise TtsCardSheetRenderError("TTS card sheet disappeared before rendering.")
    target_revision = sheet.desired_revision
    target_fingerprint = sheet.desired_fingerprint
    try:
        layout = get_tts_card_sheet_layout(sheet.layout_version)
    except TtsCardSheetRenderError as exc:
        mark_render_failed(
            sheet_id=str(sheet.id),
            error=str(exc),
        )
        raise
    output_dir = settings.tts_card_sheets_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        canvas = Image.new("RGB", layout.image_size, _BACKGROUND)
        for slot in sheet.slots.all():
            image_path = resolve_storage_path(slot.image_stored_path)
            if not image_path.is_file():
                raise TtsCardSheetRenderError(
                    f"Card image for sheet {sheet.id} slot {slot.slot_index} is unavailable."
                )
            with Image.open(image_path) as source_image:
                normalized = ImageOps.exif_transpose(source_image).convert("RGB")
                contained = ImageOps.contain(
                    normalized,
                    (layout.cell_width, layout.cell_height),
                    Image.Resampling.LANCZOS,
                )
                cell = Image.new("RGB", (layout.cell_width, layout.cell_height), _BACKGROUND)
                cell.paste(
                    contained,
                    (
                        (layout.cell_width - contained.width) // 2,
                        (layout.cell_height - contained.height) // 2,
                    ),
                )
            x = (slot.slot_index % layout.columns) * layout.cell_width
            y = (slot.slot_index // layout.columns) * layout.cell_height
            canvas.paste(cell, (x, y))

        with tempfile.NamedTemporaryFile(
            prefix=f".{sheet.id}.",
            suffix=".webp.tmp",
            dir=output_dir,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        canvas.save(temporary_path, format="WEBP", quality=90, method=6)
        with Image.open(temporary_path) as validation_image:
            if validation_image.size != layout.image_size:
                raise TtsCardSheetRenderError("Rendered TTS sheet has unexpected dimensions.")
            validation_image.verify()
        rendered_checksum = _sha256_file(temporary_path)
        target = tts_card_sheet_path(str(sheet.id), rendered_checksum)
        os.replace(temporary_path, target)
        temporary_path = None
        return mark_render_succeeded(
            sheet_id=str(sheet.id),
            rendered_revision=target_revision,
            rendered_fingerprint=target_fingerprint,
            rendered_checksum=rendered_checksum,
        )
    except Exception as exc:
        mark_render_failed(sheet_id=str(sheet.id), error=str(exc))
        if isinstance(exc, TtsCardSheetRenderError):
            raise
        raise TtsCardSheetRenderError(str(exc)) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "TtsCardSheetLayout",
    "TtsCardSheetRenderError",
    "get_tts_card_sheet_layout",
    "render_claimed_sheet",
    "tts_card_sheet_path",
]
