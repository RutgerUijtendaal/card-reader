from __future__ import annotations

import json

from card_reader_core.repositories.helpers import normalize_slug_key

SUPPORTED_SYMBOL_DETECTOR_TYPES = {"template"}


class CatalogInputNormalizer:
    def normalize_label(self, label: str) -> str:
        compact = " ".join(label.split()).strip()
        if not compact:
            raise ValueError("Label is required")
        return compact

    def normalize_key(self, *, key: str | None, label: str) -> str:
        source = key if key is not None and key.strip() else label
        normalized = normalize_slug_key(source)
        if not normalized:
            raise ValueError("Key is invalid")
        return normalized

    def normalize_identifiers_json(self, label: str, identifiers: list[str] | None) -> list[str]:
        return self.normalize_identifiers(label, identifiers)

    def normalize_identifiers(self, label: str, identifiers: list[str] | None) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()

        canonical_identifier = " ".join(label.split()).strip().lower()
        if canonical_identifier:
            seen.add(canonical_identifier)
            out.append(canonical_identifier)

        if identifiers is None:
            return out

        for raw_identifier in identifiers:
            compact = " ".join(str(raw_identifier).split()).strip().lower()
            if not compact or compact in seen:
                continue
            seen.add(compact)
            out.append(compact)
        return out

    def validate_symbol_config_json(
        self,
        object_json: str | None,
        array_json: str | None,
        *,
        field_name: str = "detection_config_json",
    ) -> None:
        if object_json is not None and not isinstance(
            self.normalize_object_json(object_json, field_name=field_name),
            dict,
        ):
            raise ValueError(f"{field_name} must be a JSON object")
        if array_json is None:
            return
        parsed = self.normalize_array_json(array_json)
        if not isinstance(parsed, list):
            raise ValueError("reference_assets_json must be a JSON array")
        if not all(isinstance(item, str) for item in parsed):
            raise ValueError("reference_assets_json entries must be strings")

    def normalize_object_json(
        self,
        value: str | None,
        *,
        field_name: str = "detection_config_json",
    ) -> dict[str, object]:
        raw = (value or "").strip() or "{}"
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError(f"{field_name} must be a JSON object")
        return {str(key): parsed[key] for key in parsed}

    def normalize_array_json(self, value: str | None) -> list[str]:
        raw = (value or "").strip() or "[]"
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("reference_assets_json must be a JSON array")
        out: list[str] = []
        for item in parsed:
            if not isinstance(item, str):
                raise ValueError("reference_assets_json entries must be strings")
            compact = item.strip()
            if compact:
                out.append(compact)
        return out

    def normalize_detector_type(self, value: str | None) -> str:
        detector_type = (value or "template").strip().lower() or "template"
        if detector_type not in SUPPORTED_SYMBOL_DETECTOR_TYPES:
            allowed = ", ".join(sorted(SUPPORTED_SYMBOL_DETECTOR_TYPES))
            raise ValueError(f"detector_type must be one of: {allowed}")
        return detector_type

    def normalize_symbol_type(self, value: str | None) -> str:
        symbol_type = normalize_slug_key((value or "generic").strip())
        if not symbol_type:
            raise ValueError("symbol_type is invalid")
        return symbol_type
