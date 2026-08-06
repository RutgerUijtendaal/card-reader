from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from django.http import FileResponse
from django.utils.http import http_date, quote_etag
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.cards.file_views import file_response
from card_reader_core.repositories.cards import (
    get_card_image,
    list_matching_cards,
    resolve_image_file_path,
)


@dataclass(frozen=True)
class _CardImageCandidate:
    card_id: str
    card_version_id: str
    checksum: str
    path: Path


@dataclass
class _RotationState:
    last_served_checksum: str | None = None
    pending_checksum: str | None = None
    pending_last_modified_epoch: int | None = None
    last_modified_epoch: int = 0


_rotation_lock = Lock()
_rotation_state = _RotationState()


class TtsCacheTestCardImageView(APIView):
    """Temporary single-process endpoint for manually verifying TTS cache refreshes."""

    permission_classes = [AllowAny]

    def head(self, _request: Request) -> FileResponse | Response:
        candidates = _list_candidates()
        if len(candidates) < 2:
            return _insufficient_candidates_response()
        candidate, last_modified_epoch = _reserve_next_candidate(candidates)
        return _candidate_response(candidate, last_modified_epoch)

    def get(self, _request: Request) -> FileResponse | Response:
        candidates = _list_candidates()
        if len(candidates) < 2:
            return _insufficient_candidates_response()
        candidate, last_modified_epoch = _consume_next_candidate(candidates)
        return _candidate_response(candidate, last_modified_epoch)


def _list_candidates() -> list[_CardImageCandidate]:
    candidates_by_checksum: dict[str, _CardImageCandidate] = {}
    rows = list_matching_cards(
        query=None,
        max_confidence=None,
        lifecycle_status="active",
    )
    for row in rows:
        image = get_card_image(row.version.id)
        if image is None:
            continue
        checksum = image.checksum.strip()
        if not checksum or checksum in candidates_by_checksum:
            continue
        image_path = resolve_image_file_path(image)
        if image_path is None:
            continue
        candidates_by_checksum[checksum] = _CardImageCandidate(
            card_id=str(row.version.card.id),
            card_version_id=str(row.version.id),
            checksum=checksum,
            path=image_path,
        )
    return sorted(
        candidates_by_checksum.values(),
        key=lambda candidate: (candidate.card_id, candidate.card_version_id, candidate.checksum),
    )[:2]


def _reserve_next_candidate(
    candidates: list[_CardImageCandidate],
) -> tuple[_CardImageCandidate, int]:
    with _rotation_lock:
        pending = _candidate_with_checksum(candidates, _rotation_state.pending_checksum)
        if pending is not None and _rotation_state.pending_last_modified_epoch is not None:
            return pending, _rotation_state.pending_last_modified_epoch

        candidate = _candidate_after(candidates, _rotation_state.last_served_checksum)
        last_modified_epoch = _advance_last_modified_epoch()
        _rotation_state.pending_checksum = candidate.checksum
        _rotation_state.pending_last_modified_epoch = last_modified_epoch
        return candidate, last_modified_epoch


def _consume_next_candidate(
    candidates: list[_CardImageCandidate],
) -> tuple[_CardImageCandidate, int]:
    with _rotation_lock:
        candidate = _candidate_with_checksum(candidates, _rotation_state.pending_checksum)
        last_modified_epoch = _rotation_state.pending_last_modified_epoch
        if candidate is None or last_modified_epoch is None:
            candidate = _candidate_after(candidates, _rotation_state.last_served_checksum)
            last_modified_epoch = _advance_last_modified_epoch()

        _rotation_state.last_served_checksum = candidate.checksum
        _rotation_state.pending_checksum = None
        _rotation_state.pending_last_modified_epoch = None
        return candidate, last_modified_epoch


def _candidate_after(
    candidates: list[_CardImageCandidate],
    previous_checksum: str | None,
) -> _CardImageCandidate:
    for candidate in candidates:
        if candidate.checksum != previous_checksum:
            return candidate
    return candidates[0]


def _candidate_with_checksum(
    candidates: list[_CardImageCandidate],
    checksum: str | None,
) -> _CardImageCandidate | None:
    if checksum is None:
        return None
    return next((candidate for candidate in candidates if candidate.checksum == checksum), None)


def _advance_last_modified_epoch() -> int:
    next_epoch = max(int(time.time()), _rotation_state.last_modified_epoch + 1)
    _rotation_state.last_modified_epoch = next_epoch
    return next_epoch


def _candidate_response(candidate: _CardImageCandidate, last_modified_epoch: int) -> FileResponse:
    response = file_response(candidate.path, "TTS cache-test card image is missing")
    response["Cache-Control"] = "public, no-cache"
    response["ETag"] = quote_etag(candidate.checksum)
    response["Last-Modified"] = http_date(last_modified_epoch)
    response["X-Card-Reader-Card-Id"] = candidate.card_id
    response["X-Card-Reader-Card-Version-Id"] = candidate.card_version_id
    response["X-Card-Reader-Image-Checksum"] = candidate.checksum
    return response


def _insufficient_candidates_response() -> Response:
    return Response(
        {
            "detail": (
                "At least two distinct readable active card images are required "
                "for the TTS cache test."
            )
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
