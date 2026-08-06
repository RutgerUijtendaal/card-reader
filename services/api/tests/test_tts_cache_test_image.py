from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from django.test import Client

from card_reader_api.cards import tts_cache_test


@pytest.fixture(autouse=True)
def _reset_rotation_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tts_cache_test, "_rotation_state", tts_cache_test._RotationState())


def test_public_cache_test_image_alternates_between_direct_gets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = _candidates(tmp_path)
    monkeypatch.setattr(tts_cache_test, "_list_candidates", lambda: candidates)
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
    monkeypatch.setattr(tts_cache_test, "_list_candidates", lambda: candidates)
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
        "_list_candidates",
        lambda: _candidates(tmp_path)[:candidate_count],
    )

    response = Client(HTTP_HOST="localhost").get("/tts/cache-test/card-image")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "At least two distinct readable active card images are required for the TTS cache test."
    )


def test_candidate_selection_requests_active_cards_and_skips_missing_or_duplicate_images(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readable_a = tmp_path / "a.webp"
    readable_a.write_bytes(b"a")
    readable_b = tmp_path / "b.webp"
    readable_b.write_bytes(b"b")
    rows = [
        _card_row("version-b", "card-b"),
        _card_row("version-a", "card-a"),
        _card_row("version-duplicate", "card-c"),
        _card_row("version-missing", "card-d"),
    ]
    images = {
        "version-a": SimpleNamespace(checksum="checksum-a", path=readable_a),
        "version-b": SimpleNamespace(checksum="checksum-b", path=readable_b),
        "version-duplicate": SimpleNamespace(checksum="checksum-a", path=readable_a),
        "version-missing": SimpleNamespace(checksum="checksum-missing", path=None),
    }
    query_arguments: dict[str, object] = {}

    def list_rows(**kwargs: object) -> list[SimpleNamespace]:
        query_arguments.update(kwargs)
        return rows

    monkeypatch.setattr(tts_cache_test, "list_matching_cards", list_rows)
    monkeypatch.setattr(
        tts_cache_test,
        "get_card_image",
        lambda version_id: images[version_id],
    )
    monkeypatch.setattr(
        tts_cache_test,
        "resolve_image_file_path",
        lambda image: image.path,
    )

    candidates = tts_cache_test._list_candidates()

    assert query_arguments["lifecycle_status"] == "active"
    assert [(candidate.card_id, candidate.checksum) for candidate in candidates] == [
        ("card-a", "checksum-a"),
        ("card-b", "checksum-b"),
    ]


def _candidates(tmp_path: Path) -> list[tts_cache_test._CardImageCandidate]:
    first_path = tmp_path / "first.webp"
    first_path.write_bytes(b"first-card-image")
    second_path = tmp_path / "second.webp"
    second_path.write_bytes(b"second-card-image")
    return [
        tts_cache_test._CardImageCandidate(
            card_id="card-a",
            card_version_id="version-a",
            checksum="checksum-a",
            path=first_path,
        ),
        tts_cache_test._CardImageCandidate(
            card_id="card-b",
            card_version_id="version-b",
            checksum="checksum-b",
            path=second_path,
        ),
    ]


def _card_row(version_id: str, card_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        version=SimpleNamespace(
            id=version_id,
            card=SimpleNamespace(id=card_id),
        )
    )


def _response_body(response: object) -> bytes:
    return b"".join(response.streaming_content)
