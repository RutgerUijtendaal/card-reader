from __future__ import annotations

from pathlib import Path

from django.http import FileResponse, Http404

from card_reader_core.config.settings import settings
from card_reader_core.models import Card, CardBack, CardVersionImage
from card_reader_core.storage import relativize_image_storage_path


def immutable_card_image_response(relative_path: str) -> FileResponse:
    normalized = Path(relative_path).as_posix().strip("/")
    images_root = (settings.storage_root_dir.resolve() / "images").resolve()
    requested_path = (settings.storage_root_dir.resolve() / normalized).resolve()
    try:
        requested_path.relative_to(images_root)
    except ValueError as exc:
        raise Http404("Card image not found") from exc
    return file_response(requested_path, "Card image not found")


def cards_for_immutable_image(relative_path: str) -> list[Card]:
    normalized = Path(relative_path).as_posix().strip("/")
    filename = Path(normalized).name
    cards: dict[str, Card] = {}
    for image in CardVersionImage.objects.select_related("card_version__card").filter(
        stored_path__endswith=filename
    ):
        try:
            stored_path = Path(relativize_image_storage_path(image.stored_path)).as_posix().strip("/")
        except ValueError:
            continue
        if stored_path == normalized:
            card = image.card_version.card
            cards[card.id] = card
    return list(cards.values())


def card_back_owns_immutable_image(relative_path: str) -> bool:
    normalized = Path(relative_path).as_posix().strip("/")
    filename = Path(normalized).name
    for stored_path in CardBack.objects.filter(stored_path__endswith=filename).values_list(
        "stored_path", flat=True
    ):
        try:
            card_back_path = Path(relativize_image_storage_path(stored_path)).as_posix().strip("/")
        except ValueError:
            continue
        if card_back_path == normalized:
            return True
    return False


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
