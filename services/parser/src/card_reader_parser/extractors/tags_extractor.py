from __future__ import annotations


class TagsExtractor:
    def extract(self, middle_text: str) -> list[str]:
        _, tags_part = self._split_middle_text(middle_text)
        if not tags_part:
            return []

        if "," in tags_part:
            raw_tags = [part.strip() for part in tags_part.split(",")]
        else:
            raw_tags = [part.strip() for part in tags_part.split()]

        out: list[str] = []
        seen: set[str] = set()
        for tag in raw_tags:
            if not tag:
                continue
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(tag)
        return out

    def _split_middle_text(self, middle_text: str) -> tuple[str, str]:
        text = " ".join(middle_text.split()).strip()
        if not text:
            return "", ""
        if "-" not in text:
            return text, ""
        left, right = text.split("-", 1)
        return left.strip(), right.strip()

