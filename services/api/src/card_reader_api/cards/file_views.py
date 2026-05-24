from __future__ import annotations

from pathlib import Path

from django.http import FileResponse, Http404

from card_reader_core.settings import settings


def immutable_card_image_response(relative_path: str) -> FileResponse:
    normalized = Path(relative_path).as_posix().strip("/")
    images_root = (settings.storage_root_dir.resolve() / "images").resolve()
    requested_path = (settings.storage_root_dir.resolve() / normalized).resolve()
    try:
        requested_path.relative_to(images_root)
    except ValueError as exc:
        raise Http404("Card image not found") from exc
    return file_response(requested_path, "Card image not found")


def symbol_asset_response(asset_path: str) -> FileResponse:
    symbols_root = (settings.storage_root_dir.resolve() / "symbols").resolve()
    requested_path = (symbols_root / asset_path).resolve()
    try:
        requested_path.relative_to(symbols_root)
    except ValueError as exc:
        raise Http404("Symbol asset not found") from exc
    return file_response(requested_path, "Symbol asset not found")


def file_response(path: Path, detail: str) -> FileResponse:
    if not path.exists() or not path.is_file():
        raise Http404(detail)
    return FileResponse(path.open("rb"))
