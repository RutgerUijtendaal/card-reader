from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Sequence

from .matching import KnownMetadataEntry, KnownMetadataMatcher

SuggestionKind = Literal["tag", "type"]
MIDDLE_TEXT_SEPARATOR_PATTERN = re.compile(r"\s-\s")


@dataclass(frozen=True)
class MetadataSuggestionDraft:
    display_value: str
    normalized_value: str
    source_text: str
    normalized_source_text: str


def split_middle_text(middle_text: str) -> tuple[str, str]:
    text = " ".join(middle_text.split()).strip()
    if not text:
        return "", ""
    separator_match = MIDDLE_TEXT_SEPARATOR_PATTERN.search(text)
    if separator_match is None:
        return text, ""
    left = text[: separator_match.start()]
    right = text[separator_match.end() :]
    return left.strip(), right.strip()


def extract_metadata_ids_and_suggestions(
    text: str,
    entries: Sequence[KnownMetadataEntry],
    *,
    kind: SuggestionKind,
    matcher: KnownMetadataMatcher | None = None,
) -> tuple[list[str], list[MetadataSuggestionDraft]]:
    effective_matcher = matcher or KnownMetadataMatcher()
    normalized_source_text = effective_matcher.normalize_candidate(text)
    if not normalized_source_text:
        return [], []

    ids = effective_matcher.extract_ids(normalized_source_text, entries)
    leftover = effective_matcher.remove_matches(normalized_source_text, entries)
    if not leftover:
        return ids, []

    if kind == "tag":
        segments = split_tag_suggestion_segments(leftover, matcher=effective_matcher)
    else:
        normalized_segment = normalize_suggestion_segment(leftover, matcher=effective_matcher)
        segments = [normalized_segment] if normalized_segment else []

    return ids, [
        MetadataSuggestionDraft(
            display_value=segment,
            normalized_value=segment.lower(),
            source_text=text,
            normalized_source_text=normalized_source_text,
        )
        for segment in segments
    ]


def split_tag_suggestion_segments(
    text: str,
    *,
    matcher: KnownMetadataMatcher | None = None,
) -> list[str]:
    effective_matcher = matcher or KnownMetadataMatcher()
    raw_segments = text.split(",") if "," in text else text.split()
    out: list[str] = []
    seen: set[str] = set()
    for raw_segment in raw_segments:
        segment = normalize_suggestion_segment(raw_segment, matcher=effective_matcher)
        if not segment:
            continue
        folded = segment.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        out.append(segment)
    return out


def normalize_suggestion_segment(
    text: str,
    *,
    matcher: KnownMetadataMatcher | None = None,
) -> str:
    effective_matcher = matcher or KnownMetadataMatcher()
    normalized = effective_matcher.normalize_candidate(text.replace(",", " "))
    if not normalized:
        return ""
    if all(not char.isalnum() for char in normalized):
        return ""
    return normalized
