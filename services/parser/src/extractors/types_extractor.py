from __future__ import annotations

import re


class TypesExtractor:
    _modifier_pattern = re.compile(r"(?<!\w)unique(?!\w)", re.IGNORECASE)

    def extract(self, middle_text: str) -> list[str]:
        type_part, _ = self._split_middle_text(middle_text)
        if not type_part:
            return []

        out: list[str] = []
        had_unique = bool(self._modifier_pattern.search(type_part))
        if had_unique:
            out.append("Unique")

        stripped = self._modifier_pattern.sub(" ", type_part)
        stripped = " ".join(stripped.split()).strip()
        if stripped:
            out.append(stripped)

        deduped: list[str] = []
        seen: set[str] = set()
        for item in out:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _split_middle_text(self, middle_text: str) -> tuple[str, str]:
        text = " ".join(middle_text.split()).strip()
        if not text:
            return "", ""
        if "-" not in text:
            return text, ""
        left, right = text.split("-", 1)
        return left.strip(), right.strip()
