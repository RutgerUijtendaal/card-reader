from __future__ import annotations

import json
import math
from typing import Any

from card_reader_core.models import Template
from card_reader_core.repositories.helpers import normalize_slug_key
from card_reader_core.repositories.templates import (
    create_template,
    delete_template,
    get_template,
    get_template_by_key,
    list_templates,
    template_key_exists,
    update_template,
)
from .parser_types import (
    MAX_MANA_BADGE_OCR_ATTEMPTS,
    MAX_MANA_BADGE_OCR_SCALE,
    NAME_PRODUCING_TEMPLATE_PARSER_TYPES,
    NAME_MANA_COST,
    SUPPORTED_TEMPLATE_PARSER_TYPES,
    TEMPLATE_PARSER_TYPES,
)


class TemplateService:
    def list_templates(self) -> list[Template]:
        return list_templates()

    def get_template(self, entry_id: str) -> Template | None:
        return get_template(entry_id)

    def get_template_by_key(self, key: str) -> Template | None:
        return get_template_by_key(key=key)

    def get_template_definition(self, key: str) -> dict[str, Any]:
        row = self.get_template_by_key(key)
        if row is None:
            raise FileNotFoundError(f"Template '{key}' does not exist")

        if isinstance(row.definition_json, str):
            return self._normalize_definition_json(row.definition_json)
        if not isinstance(row.definition_json, dict):
            raise ValueError(f"Template '{key}' definition_json must be a JSON object")
        return self._validate_template_definition(row.definition_json)

    def create_template(
        self,
        *,
        label: str,
        key: str | None = None,
        definition_json: str,
    ) -> Template:
        normalized_label = self._normalize_label(label)
        normalized_key = self._normalize_key(key=key, label=normalized_label)
        self._ensure_unique_template_key(normalized_key)
        return create_template(
            key=normalized_key,
            label=normalized_label,
            definition_json=self._normalize_definition_json(definition_json),
        )

    def update_template(
        self,
        *,
        entry_id: str,
        label: str | None = None,
        key: str | None = None,
        definition_json: str | None = None,
    ) -> Template | None:
        row = get_template(entry_id)
        if row is None:
            return None

        updates: dict[str, object] = {}
        current_label = row.label
        if label is not None:
            current_label = self._normalize_label(label)
            updates["label"] = current_label
        if key is not None:
            raise ValueError("Template key cannot be changed")
        if definition_json is not None:
            updates["definition_json"] = self._normalize_definition_json(definition_json)
        return update_template(entry_id=entry_id, updates=updates)

    def delete_template(self, *, entry_id: str) -> bool:
        return delete_template(entry_id=entry_id)

    def _ensure_unique_template_key(self, key: str, exclude_id: str | None = None) -> None:
        if template_key_exists(key=key, exclude_id=exclude_id):
            raise ValueError(f"Key '{key}' already exists")

    def _normalize_key(self, *, key: str | None, label: str) -> str:
        source = key if key is not None and key.strip() else label
        normalized = normalize_slug_key(source)
        if not normalized:
            raise ValueError("Key is invalid")
        return normalized

    def _normalize_label(self, label: str) -> str:
        compact = " ".join(label.split()).strip()
        if not compact:
            raise ValueError("Label is required")
        return compact

    def _normalize_definition_json(self, definition_json: str) -> dict[str, Any]:
        raw = definition_json.strip()
        if not raw:
            raise ValueError("definition_json is required")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("definition_json must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("definition_json must be a JSON object")
        return self._validate_template_definition(parsed)

    def _validate_template_definition(self, definition: dict[str, Any]) -> dict[str, Any]:
        regions = definition.get("regions")
        if not isinstance(regions, list) or not regions:
            raise ValueError("definition_json.regions must be a non-empty array")

        seen_region_ids: set[str] = set()
        name_region: tuple[int, str, str] | None = None
        normalized_regions: list[dict[str, Any]] = []
        for index, region in enumerate(regions):
            normalized_region, name_region_candidate = self._normalize_region_definition(
                region,
                index=index,
            )
            region_id = normalized_region["region_id"]
            if region_id in seen_region_ids:
                raise ValueError(f"definition_json.regions[{index}].region_id must be unique")
            seen_region_ids.add(region_id)

            if name_region_candidate is not None:
                if name_region is not None:
                    previous_index, previous_region_id, previous_parser_type = name_region
                    raise ValueError(
                        f"definition_json.regions[{index}].parser_type conflicts with "
                        f"name-producing region '{previous_region_id}' at index "
                        f"{previous_index} ({previous_parser_type}); only one of name or "
                        "name_mana_cost may be configured"
                    )
                name_region = name_region_candidate
            normalized_regions.append(normalized_region)

        normalized_definition = dict(definition)
        normalized_definition["regions"] = normalized_regions
        return normalized_definition

    def _normalize_region_definition(
        self,
        region: object,
        *,
        index: int,
    ) -> tuple[dict[str, Any], tuple[int, str, str] | None]:
        field = f"definition_json.regions[{index}]"
        if not isinstance(region, dict):
            raise ValueError(f"{field} must be an object")

        region_id = str(region.get("region_id", "")).strip()
        if not region_id:
            raise ValueError(f"{field}.region_id is required")

        parser_type = str(region.get("parser_type", "")).strip()
        if parser_type not in SUPPORTED_TEMPLATE_PARSER_TYPES:
            supported = ", ".join(TEMPLATE_PARSER_TYPES)
            raise ValueError(f"{field}.parser_type must be one of: {supported}")

        cut_region = region.get("cut_region")
        if not isinstance(cut_region, dict):
            raise ValueError(f"{field}.cut_region must be an object")
        ocr_config = region.get("ocr_config", {})
        if not isinstance(ocr_config, dict):
            raise ValueError(f"{field}.ocr_config must be an object")

        mana_badge_ocr = region.get("mana_badge_ocr")
        if mana_badge_ocr is not None:
            self._validate_mana_badge_ocr(
                mana_badge_ocr,
                index=index,
                parser_type=parser_type,
            )

        normalized_region = dict(region)
        normalized_region["region_id"] = region_id
        normalized_region["parser_type"] = parser_type
        normalized_region["cut_region"] = cut_region
        normalized_region["ocr_config"] = ocr_config
        name_region = None
        if parser_type in NAME_PRODUCING_TEMPLATE_PARSER_TYPES:
            name_region = (index, region_id, parser_type)
        return normalized_region, name_region

    def _validate_mana_badge_ocr(
        self,
        config: object,
        *,
        index: int,
        parser_type: str,
    ) -> None:
        field = f"definition_json.regions[{index}].mana_badge_ocr"
        if parser_type != NAME_MANA_COST:
            raise ValueError(f"{field} is supported only for name_mana_cost regions")
        if not isinstance(config, dict):
            raise ValueError(f"{field} must be an object")
        cut_region = config.get("cut_region")
        if not isinstance(cut_region, dict):
            raise ValueError(f"{field}.cut_region must be an object")
        self._validate_mana_badge_cut_region(cut_region, field=f"{field}.cut_region")

        scales = config.get("scales")
        if scales is None:
            return
        if not isinstance(scales, list) or not scales:
            raise ValueError(f"{field}.scales must be a non-empty array")
        if len(scales) > MAX_MANA_BADGE_OCR_ATTEMPTS:
            raise ValueError(
                f"{field}.scales may contain at most {MAX_MANA_BADGE_OCR_ATTEMPTS} values"
            )
        if any(
            not isinstance(scale, int)
            or isinstance(scale, bool)
            or not 1 <= scale <= MAX_MANA_BADGE_OCR_SCALE
            for scale in scales
        ):
            raise ValueError(
                f"{field}.scales values must be integers from 1 to {MAX_MANA_BADGE_OCR_SCALE}"
            )

    def _validate_mana_badge_cut_region(
        self,
        bounds: dict[str, object],
        *,
        field: str,
    ) -> None:
        unit = str(bounds.get("unit", "relative")).strip().lower()
        if unit not in {"relative", "absolute"}:
            raise ValueError(f"{field}.unit must be relative or absolute")

        values: dict[str, float] = {}
        for key in ("x", "y", "w", "h"):
            raw = bounds.get(key)
            if (
                not isinstance(raw, (int, float))
                or isinstance(raw, bool)
                or not math.isfinite(raw)
            ):
                raise ValueError(f"{field}.{key} must be a finite number")
            values[key] = float(raw)

        if values["x"] < 0 or values["y"] < 0:
            raise ValueError(f"{field}.x and {field}.y must be non-negative")
        if values["w"] <= 0 or values["h"] <= 0:
            raise ValueError(f"{field}.w and {field}.h must be greater than zero")
        if unit == "relative" and (
            values["x"] + values["w"] > 1 or values["y"] + values["h"] > 1
        ):
            raise ValueError(f"{field} must fit within the relative parent region")
