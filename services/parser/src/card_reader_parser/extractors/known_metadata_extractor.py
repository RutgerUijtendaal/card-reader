from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Pattern, Protocol, Sequence


class KnownMetadataEntry(Protocol):
    id: str
    label: str
    identifiers_json: list[str] | str


class KnownMetadataExtractor:
    def __init__(self) -> None:
        self._pattern_cache: dict[str, Pattern[str]] = {}

    def extract_ids(self, text: str, entries: Sequence[KnownMetadataEntry]) -> list[str]:
        if not text.strip():
            return []

        return [match.entry.id for match in self.extract_matches(text, entries)]

    def extract_matches(
        self,
        text: str,
        entries: Sequence[KnownMetadataEntry],
    ) -> list["KnownMetadataMatch"]:
        if not text.strip():
            return []

        matched_entries: list[KnownMetadataMatch] = []
        for entry in entries:
            terms = self._terms_for_entry(entry)
            if not terms:
                continue
            matched_terms = [term for term in terms if self._pattern_for_label(term).search(text)]
            if matched_terms:
                matched_entries.append(KnownMetadataMatch(entry=entry, matched_terms=matched_terms))
        return matched_entries

    def remove_matches(self, text: str, entries: Sequence[KnownMetadataEntry]) -> str:
        spans = self._match_spans(text, entries)
        if not spans:
            return self.normalize_candidate(text)

        kept: list[tuple[int, int]] = []
        last_end = -1
        for start, end in sorted(spans, key=lambda item: (item[0], -(item[1] - item[0]))):
            if start < last_end:
                continue
            kept.append((start, end))
            last_end = end

        out: list[str] = []
        cursor = 0
        for start, end in kept:
            out.append(text[cursor:start])
            out.append(" ")
            cursor = end
        out.append(text[cursor:])
        return self.normalize_candidate("".join(out))

    def normalize_candidate(self, text: str) -> str:
        return " ".join(text.split()).strip()

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

    def _terms_for_entry(self, entry: KnownMetadataEntry) -> list[str]:
        terms: list[str] = []
        seen: set[str] = set()
        for raw_term in [entry.label, *self._load_identifiers(entry)]:
            term = raw_term.strip()
            if not term:
                continue
            folded = term.casefold()
            if folded in seen:
                continue
            seen.add(folded)
            terms.append(term)
        return terms

    def _load_identifiers(self, entry: KnownMetadataEntry) -> list[str]:
        payload = entry.identifiers_json or []
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, str)]

    def _match_spans(self, text: str, entries: Sequence[KnownMetadataEntry]) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        for entry in entries:
            for term in self._terms_for_entry(entry):
                spans.extend((match.start(), match.end()) for match in self._pattern_for_label(term).finditer(text))
        return spans


@dataclass(frozen=True)
class KnownMetadataMatch:
    entry: KnownMetadataEntry
    matched_terms: list[str]
