from __future__ import annotations

import json
import re
from typing import Pattern, Sequence

from card_reader_core.models import Keyword


class KeywordsExtractor:
    def __init__(self) -> None:
        self._pattern_cache: dict[str, Pattern[str]] = {}

    def extract_keyword_ids(self, text: str, keywords: Sequence[Keyword]) -> list[str]:
        if not text.strip():
            return []

        matched_ids: list[str] = []
        for keyword in keywords:
            terms = self._terms_for_keyword(keyword)
            if not terms:
                continue
            if any(self._pattern_for_label(term).search(text) for term in terms):
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
        compiled = re.compile(escaped, re.IGNORECASE)
        self._pattern_cache[label] = compiled
        return compiled

    def _terms_for_keyword(self, keyword: Keyword) -> list[str]:
        terms: list[str] = []
        seen: set[str] = set()
        for raw_term in [keyword.label, *self._load_identifiers(keyword)]:
            term = raw_term.strip()
            if not term:
                continue
            folded = term.casefold()
            if folded in seen:
                continue
            seen.add(folded)
            terms.append(term)
        return terms

    def _load_identifiers(self, keyword: Keyword) -> list[str]:
        try:
            payload = json.loads(keyword.identifiers_json or "[]")
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, str)]

