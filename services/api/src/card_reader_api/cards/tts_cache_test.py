from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock

from django.http import FileResponse
from django.utils.http import http_date, quote_etag
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from card_reader_api.cards.file_views import file_response
from card_reader_core.repositories.cards import CardImageSource, list_latest_active_card_image_sources


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
        candidates = list_latest_active_card_image_sources(limit=2)
        if len(candidates) < 2:
            return _insufficient_candidates_response()
        candidate, last_modified_epoch = _reserve_next_candidate(candidates)
        return _candidate_response(candidate, last_modified_epoch)

    def get(self, _request: Request) -> FileResponse | Response:
        candidates = list_latest_active_card_image_sources(limit=2)
        if len(candidates) < 2:
            return _insufficient_candidates_response()
        candidate, last_modified_epoch = _consume_next_candidate(candidates)
        return _candidate_response(candidate, last_modified_epoch)


def _reserve_next_candidate(
    candidates: list[CardImageSource],
) -> tuple[CardImageSource, int]:
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
    candidates: list[CardImageSource],
) -> tuple[CardImageSource, int]:
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
    candidates: list[CardImageSource],
    previous_checksum: str | None,
) -> CardImageSource:
    for candidate in candidates:
        if candidate.checksum != previous_checksum:
            return candidate
    return candidates[0]


def _candidate_with_checksum(
    candidates: list[CardImageSource],
    checksum: str | None,
) -> CardImageSource | None:
    if checksum is None:
        return None
    return next((candidate for candidate in candidates if candidate.checksum == checksum), None)


def _advance_last_modified_epoch() -> int:
    next_epoch = max(int(time.time()), _rotation_state.last_modified_epoch + 1)
    _rotation_state.last_modified_epoch = next_epoch
    return next_epoch


def _candidate_response(candidate: CardImageSource, last_modified_epoch: int) -> FileResponse:
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
