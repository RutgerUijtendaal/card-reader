from __future__ import annotations

import re
from typing import Pattern, Sequence

from models import Keyword


class KeywordsExtractor:
    def __init__(self) -> None:
        self._pattern_cache: dict[str, Pattern[str]] = {}

    def extract_keyword_ids(self, text: str, keywords: Sequence[Keyword]) -> list[str]:
        if not text.strip():
            return []

        matched_ids: list[str] = []
        for keyword in keywords:
            label = keyword.label.strip()
            if not label:
                continue
            pattern = self._pattern_for_label(label)
            if pattern.search(text):
                matched_ids.append(keyword.id)
        return matched_ids

    def _pattern_for_label(self, label: str) -> Pattern[str]:
        cached = self._pattern_cache.get(label)
        if cached is not None:
            return cached

        escaped = re.escape(label)
        if label and label[0].isalnum():
            escaped = r"(?<!\w)" + escaped
        if label and label[-1].isalnum():
            escaped = escaped + r"(?!\w)"
        compiled = re.compile(escaped)
        self._pattern_cache[label] = compiled
        return compiled
