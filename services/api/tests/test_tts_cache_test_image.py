from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from card_reader_api.cards import tts_cache_test
from card_reader_core.config.settings import settings
from card_reader_core.models import Card, CardVersion, CardVersionImage, Template
from card_reader_core.repositories.cards import (
    CardImageSource,
    list_latest_active_card_image_sources,
)
from card_reader_core.storage import build_storage_relative_path


@pytest.fixture(autouse=True)
def _reset_rotation_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tts_cache_test, "_rotation_state", tts_cache_test._RotationState())


def test_public_cache_test_image_alternates_between_direct_gets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = _candidates(tmp_path)
    _set_candidates(monkeypatch, candidates)
    client = Client(HTTP_HOST="localhost")

    first = client.get("/tts/cache-test/card-image")
    second = client.get("/tts/cache-test/card-image")
    third = client.get("/tts/cache-test/card-image")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert _response_body(first) == b"first-card-image"
    assert _response_body(second) == b"second-card-image"
    assert _response_body(third) == b"first-card-image"
    assert first["X-Card-Reader-Image-Checksum"] != second[
        "X-Card-Reader-Image-Checksum"
    ]
    assert third["X-Card-Reader-Image-Checksum"] == first[
        "X-Card-Reader-Image-Checksum"
    ]
    assert len({first["Last-Modified"], second["Last-Modified"], third["Last-Modified"]}) == 3
    assert first["Cache-Control"] == "public, no-cache"
    assert first["ETag"] == '"checksum-a"'
    assert first["X-Card-Reader-Card-Id"] == "card-a"
    assert first["X-Card-Reader-Card-Version-Id"] == "version-a"


def test_cache_test_head_reserves_the_image_returned_by_the_following_get(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = _candidates(tmp_path)
    _set_candidates(monkeypatch, candidates)
    client = Client(HTTP_HOST="localhost")

    first = client.get("/tts/cache-test/card-image")
    head = client.head("/tts/cache-test/card-image")
    downloaded = client.get("/tts/cache-test/card-image")

    assert first["X-Card-Reader-Image-Checksum"] == "checksum-a"
    assert head.status_code == 200
    assert _response_body(head) == b""
    assert head["X-Card-Reader-Image-Checksum"] == "checksum-b"
    assert downloaded["X-Card-Reader-Image-Checksum"] == head[
        "X-Card-Reader-Image-Checksum"
    ]
    assert downloaded["Last-Modified"] == head["Last-Modified"]
    assert downloaded["ETag"] == head["ETag"]
    assert _response_body(downloaded) == b"second-card-image"


@pytest.mark.parametrize("candidate_count", [0, 1])
def test_cache_test_requires_two_distinct_readable_images(
    candidate_count: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tts_cache_test,
        "list_latest_active_card_image_sources",
        lambda *, limit: _candidates(tmp_path)[:candidate_count],
    )

    response = Client(HTTP_HOST="localhost").get("/tts/cache-test/card-image")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "At least two distinct readable active card images are required for the TTS cache test."
    )


def test_candidate_query_is_bounded_and_skips_deprecated_missing_or_duplicate_images() -> None:
    first = _create_card_image_source("first", checksum="bounded-a")
    second = _create_card_image_source("second", checksum="bounded-b")
    duplicate = _create_card_image_source("duplicate", checksum="bounded-a")
    missing = _create_card_image_source("missing", checksum="bounded-missing", write_file=False)
    deprecated = _create_card_image_source(
        "deprecated",
        checksum="bounded-deprecated",
        lifecycle_status="deprecated",
    )
    card_ids = [first.id, second.id, duplicate.id, missing.id, deprecated.id]

    with CaptureQueriesContext(connection) as queries:
        candidates = list_latest_active_card_image_sources(limit=2, card_ids=card_ids)

    assert len(queries) == 1
    assert "LIMIT 64" in queries[0]["sql"].upper()
    assert {candidate.checksum for candidate in candidates} == {"bounded-a", "bounded-b"}


def _candidates(tmp_path: Path) -> list[CardImageSource]:
    first_path = tmp_path / "first.webp"
    first_path.write_bytes(b"first-card-image")
    second_path = tmp_path / "second.webp"
    second_path.write_bytes(b"second-card-image")
    return [
        CardImageSource(
            card_id="card-a",
            card_version_id="version-a",
            checksum="checksum-a",
            path=first_path,
        ),
        CardImageSource(
            card_id="card-b",
            card_version_id="version-b",
            checksum="checksum-b",
            path=second_path,
        ),
    ]


def _set_candidates(
    monkeypatch: pytest.MonkeyPatch,
    candidates: list[CardImageSource],
) -> None:
    def load_candidates(*, limit: int) -> list[CardImageSource]:
        assert limit == 2
        return candidates

    monkeypatch.setattr(tts_cache_test, "list_latest_active_card_image_sources", load_candidates)


def _create_card_image_source(
    label: str,
    *,
    checksum: str,
    lifecycle_status: str = "active",
    write_file: bool = True,
) -> Card:
    suffix = uuid4().hex
    card = Card.objects.create(
        key=f"tts-cache-source-{label}-{suffix}",
        label=f"TTS Cache Source {label}",
        lifecycle_status=lifecycle_status,
    )
    version = CardVersion.objects.create(
        card=card,
        template=Template.objects.get(key="mtg-like-v1"),
        image_hash=f"tts-cache-source-{label}-{suffix}",
        name=f"TTS Cache Source {label}",
        is_latest=True,
    )
    card.latest_version = version
    card.save(update_fields=["latest_version"])
    stored_path = build_storage_relative_path("images", f"{checksum}-{suffix}.webp")
    if write_file:
        image_path = settings.storage_root_dir / stored_path
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(checksum.encode("utf-8"))
    CardVersionImage.objects.create(
        card_version=version,
        source_file=stored_path,
        stored_path=stored_path,
        checksum=checksum,
    )
    return card


def _response_body(response: object) -> bytes:
    return b"".join(response.streaming_content)
