from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from PIL import Image

from card_reader_core.config.settings import settings
from card_reader_core.storage import resolve_storage_path, store_image


@pytest.mark.parametrize("suffix", [".png", ".webp"])
def test_concurrent_identical_uploads_publish_complete_images_atomically(tmp_path: Path, monkeypatch, suffix: str) -> None:
    from card_reader_core.storage import paths

    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    source = tmp_path / f"source{suffix}"
    Image.new("RGB", (8, 8), color=(30, 40, 50)).save(source)
    target = resolve_storage_path("images/same.webp")
    barrier = Barrier(2)
    destinations: list[Path] = []
    save = Image.Image.save
    copy = paths.shutil.copy2

    def completed_temp(destination) -> None:
        destinations.append(Path(destination))
        assert not target.exists(), "An incomplete image must not be published"
        barrier.wait(timeout=10)

    def synchronized_save(image, destination, *args, **kwargs):
        save(image, destination, *args, **kwargs)
        completed_temp(destination)

    def synchronized_copy(source_path, destination, *args, **kwargs):
        result = copy(source_path, destination, *args, **kwargs)
        completed_temp(destination)
        return result

    monkeypatch.setattr(Image.Image, "save", synchronized_save)
    monkeypatch.setattr(paths.shutil, "copy2", synchronized_copy)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(store_image, source, "same") for _ in range(2)]
        assert [future.result(timeout=15) for future in futures] == ["images/same.webp"] * 2
    assert len(set(destinations)) == 2
    assert all(not path.exists() for path in destinations)
    with Image.open(target) as image:
        image.verify()


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
