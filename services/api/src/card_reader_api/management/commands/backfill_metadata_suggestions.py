from __future__ import annotations

import re
from typing import Pattern

from django.core.management.base import BaseCommand

from card_reader_core.models import CardVersion, Tag, Type
from card_reader_core.repositories.metadata_repository import (
    SuggestionCandidate,
    list_tags,
    list_types,
    replace_card_version_metadata_suggestions,
)


class Command(BaseCommand):
    help = "Backfill tag/type suggestions from latest card version type_line values."

    def handle(self, *args, **options) -> None:
        _ = args
        _ = options
        tags = list_tags()
        types = list_types()
        versions = list(CardVersion.objects.filter(is_latest=True).order_by("updated_at"))

        updated = 0
        for version in versions:
            type_text, tag_text = split_middle_text(version.type_line)
            type_candidate = build_candidate(type_text, types)
            tag_candidate = build_candidate(tag_text, tags)
            replace_card_version_metadata_suggestions(
                card_version_id=version.id,
                kind="type",
                candidates=[] if type_candidate is None else [type_candidate],
                parse_result_id=version.parse_result_id,
            )
            replace_card_version_metadata_suggestions(
                card_version_id=version.id,
                kind="tag",
                candidates=[] if tag_candidate is None else [tag_candidate],
                parse_result_id=version.parse_result_id,
            )
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Backfilled metadata suggestions for {updated} latest card versions."))


def split_middle_text(middle_text: str) -> tuple[str, str]:
    text = normalize_text(middle_text)
    if not text:
        return "", ""
    if "-" not in text:
        return text, ""
    left, right = text.split("-", 1)
    return left.strip(), right.strip()


def build_candidate(text: str, entries: list[Tag] | list[Type]) -> SuggestionCandidate | None:
    normalized_source_text = normalize_text(text)
    if not normalized_source_text:
        return None
    leftover = remove_matches(normalized_source_text, entries)
    if not leftover:
        return None
    return SuggestionCandidate(
        display_value=leftover,
        normalized_value=leftover.lower(),
        source_text=text,
        normalized_source_text=normalized_source_text,
    )


def remove_matches(text: str, entries: list[Tag] | list[Type]) -> str:
    spans: list[tuple[int, int]] = []
    for entry in entries:
        for term in terms_for_entry(entry):
            spans.extend((match.start(), match.end()) for match in pattern_for_label(term).finditer(text))

    if not spans:
        return normalize_text(text)

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
    return normalize_text("".join(out))


def normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


def terms_for_entry(entry: Tag | Type) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    raw_identifiers = entry.identifiers_json if isinstance(entry.identifiers_json, list) else []
    for raw_term in [entry.label, *raw_identifiers]:
        term = str(raw_term).strip()
        if not term:
            continue
        folded = term.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        values.append(term)
    return values


_PATTERN_CACHE: dict[str, Pattern[str]] = {}


def pattern_for_label(label: str) -> Pattern[str]:
    cached = _PATTERN_CACHE.get(label)
    if cached is not None:
        return cached
    escaped = re.escape(label)
    if label and label[0].isalnum():
        escaped = r"(?<!\w)" + escaped
    if label and label[-1].isalnum():
        escaped = escaped + r"(?!\w)"
    compiled = re.compile(escaped, re.IGNORECASE)
    _PATTERN_CACHE[label] = compiled
    return compiled
