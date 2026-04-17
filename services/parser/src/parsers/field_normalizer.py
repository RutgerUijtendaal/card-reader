from __future__ import annotations

import re


class FieldNormalizer:
    def normalize_fields(
        self,
        *,
        image_stem: str,
        top_text: str,
        type_text: str,
        rules_text: str,
    ) -> dict[str, str]:
        name = self._extract_name_from_top_bar(top_text) or image_stem
        mana_cost = self._extract_mana_hint(top_text)
        return {
            "name": name,
            "type_line": type_text,
            "mana_cost": mana_cost,
            "rules_text": rules_text,
        }

    def confidence_breakdown(
        self,
        *,
        top_confidence: float,
        type_confidence: float,
        rules_confidence: float,
        mana_cost: str,
    ) -> dict[str, float]:
        mana_conf = top_confidence * 0.8 if mana_cost else 0.0
        present_conf = [
            value for value in (top_confidence, type_confidence, rules_confidence, mana_conf) if value > 0.0
        ]
        overall = float(sum(present_conf) / len(present_conf)) if present_conf else 0.0
        return {
            "name": round(top_confidence, 3),
            "type_line": round(type_confidence, 3),
            "mana_cost": round(mana_conf, 3),
            "rules_text": round(rules_confidence, 3),
            "overall": round(overall, 3),
        }

    def _extract_name_from_top_bar(self, top_bar_text: str) -> str:
        text = top_bar_text.replace("\n", " ").strip()
        if not text:
            return ""
        text = re.sub(r"\s+\d+\s*$", "", text)
        text = re.sub(r"\s*[★☆✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿]+.*$", "", text)
        return text.strip()

    def _extract_mana_hint(self, top_bar_text: str) -> str:
        text = top_bar_text.replace("\n", " ").strip()
        if not text:
            return ""
        match = re.search(r"(\d+(?:\s*[★☆✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿xX]*)?)$", text)
        if not match:
            return ""
        return match.group(1).strip()
