from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class ImportJobItemTarget:
    card_id: str
    card_version_id: str
