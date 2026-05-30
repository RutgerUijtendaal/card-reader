from __future__ import annotations

from pathlib import Path

from PIL import Image

from card_reader_core.config.settings import settings
from card_reader_core.storage import resolve_storage_path, store_image


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color=(120, 30, 200)).save(path, format="PNG")


def _write_transparent_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (8, 8), color=(120, 30, 200, 255))
    image.putpixel((0, 0), (120, 30, 200, 0))
    image.save(path, format="PNG")


def _write_webp(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color=(30, 120, 200)).save(path, format="WEBP", quality=90)


def test_store_image_converts_png_to_canonical_webp(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    source_path = tmp_path / "uploads" / "card.png"
    _write_png(source_path)

    stored_path = store_image(source_path, "png-checksum")

    assert stored_path == "images/png-checksum.webp"
    with Image.open(resolve_storage_path(stored_path)) as image:
        assert image.format == "WEBP"
    assert source_path.exists()


def test_store_image_preserves_png_alpha_in_canonical_webp(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    source_path = tmp_path / "uploads" / "transparent-card.png"
    _write_transparent_png(source_path)

    stored_path = store_image(source_path, "transparent-checksum")

    assert stored_path == "images/transparent-checksum.webp"
    with Image.open(resolve_storage_path(stored_path)) as image:
        assert image.format == "WEBP"
        assert "A" in image.getbands()
        assert image.convert("RGBA").getpixel((0, 0))[3] == 0


def test_store_image_keeps_canonical_webp_extension_for_webp_source(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    source_path = tmp_path / "uploads" / "card.webp"
    _write_webp(source_path)

    stored_path = store_image(source_path, "webp-checksum")

    assert stored_path == "images/webp-checksum.webp"
    with Image.open(resolve_storage_path(stored_path)) as image:
        assert image.format == "WEBP"
