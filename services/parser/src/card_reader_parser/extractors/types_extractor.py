from __future__ import annotations


class TypesExtractor:
    def extract(self, middle_text: str) -> list[str]:
        type_part, _ = self._split_middle_text(middle_text)
        if not type_part:
            return []

        deduped: list[str] = []
        seen: set[str] = set()
        for type_name in type_part.split():
            key = type_name.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(type_name)
        return deduped

    def _split_middle_text(self, middle_text: str) -> tuple[str, str]:
        text = " ".join(middle_text.split()).strip()
        if not text:
            return "", ""
        if "-" not in text:
            return text, ""
        left, right = text.split("-", 1)
        return left.strip(), right.strip()

