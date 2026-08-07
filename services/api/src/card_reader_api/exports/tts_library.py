from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
from threading import Lock
import time

from django.utils.http import quote_etag

from card_reader_api.exports.tts_cards import (
    build_tts_card_export_payload,
    serialize_tts_card_export_payload,
)
from card_reader_core.services.exports import (
    TtsCardExportError,
    TtsCardExportErrorCode,
    TtsCardExportService,
)

_FILE_REVERIFICATION_SECONDS = 300.0
_MAX_STABLE_BUILD_ATTEMPTS = 3


@dataclass(frozen=True)
class TtsCardLibraryMaterialization:
    content: bytes | None
    etag: str | None
    error_code: TtsCardExportErrorCode | None
    error_detail: str | None


@dataclass(frozen=True)
class _CachedTtsCardLibraryMaterialization:
    cache_key: str
    library_revision: str
    verified_at: float
    materialization: TtsCardLibraryMaterialization


class TtsCardLibraryMaterializer:
    def __init__(self) -> None:
        self._lock = Lock()
        self._cached: _CachedTtsCardLibraryMaterialization | None = None

    def materialize(
        self,
        *,
        cache_key: str,
        absolute_url: Callable[[str], str],
    ) -> TtsCardLibraryMaterialization:
        service = TtsCardExportService()
        library_revision = service.get_library_revision()
        now = time.monotonic()
        cached = self._cached
        if cached is not None and self._is_current(cached, cache_key, library_revision, now):
            return cached.materialization

        with self._lock:
            library_revision = service.get_library_revision()
            now = time.monotonic()
            cached = self._cached
            if cached is not None and self._is_current(cached, cache_key, library_revision, now):
                return cached.materialization

            for _attempt in range(_MAX_STABLE_BUILD_ATTEMPTS):
                materialization = self._build(service, absolute_url=absolute_url)
                refreshed_revision = service.get_library_revision()
                if refreshed_revision == library_revision:
                    self._cached = _CachedTtsCardLibraryMaterialization(
                        cache_key=cache_key,
                        library_revision=library_revision,
                        verified_at=time.monotonic(),
                        materialization=materialization,
                    )
                    return materialization
                library_revision = refreshed_revision

            self._cached = None
            return TtsCardLibraryMaterialization(
                content=None,
                etag=None,
                error_code=TtsCardExportErrorCode.LIBRARY_UNSTABLE,
                error_detail=(
                    "The TTS card library changed while its manifest was being prepared. "
                    "Try again shortly."
                ),
            )

    def clear(self) -> None:
        with self._lock:
            self._cached = None

    @staticmethod
    def _is_current(
        cached: _CachedTtsCardLibraryMaterialization | None,
        cache_key: str,
        library_revision: str,
        now: float,
    ) -> bool:
        return bool(
            cached is not None
            and cached.cache_key == cache_key
            and cached.library_revision == library_revision
            and now - cached.verified_at < _FILE_REVERIFICATION_SECONDS
        )

    @staticmethod
    def _build(
        service: TtsCardExportService,
        *,
        absolute_url: Callable[[str], str],
    ) -> TtsCardLibraryMaterialization:
        try:
            export_data = service.build_library_export()
        except TtsCardExportError as exc:
            return TtsCardLibraryMaterialization(
                content=None,
                etag=None,
                error_code=exc.code,
                error_detail=exc.detail,
            )

        payload = build_tts_card_export_payload(export_data, absolute_url=absolute_url)
        content = serialize_tts_card_export_payload(payload)
        return TtsCardLibraryMaterialization(
            content=content,
            etag=quote_etag(hashlib.sha256(content).hexdigest()),
            error_code=None,
            error_detail=None,
        )


tts_card_library_materializer = TtsCardLibraryMaterializer()


__all__ = [
    "TtsCardLibraryMaterialization",
    "TtsCardLibraryMaterializer",
    "tts_card_library_materializer",
]
