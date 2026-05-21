from __future__ import annotations

import copy
import json
from typing import Any

DEFAULT_PADDLEX_OCR_CONFIG: dict[str, Any] = {
    "pipeline_name": "OCR",
    "text_type": "general",
    "use_doc_preprocessor": False,
    "use_textline_orientation": False,
    "SubModules": {
        "TextDetection": {
            "module_name": "text_detection",
            "model_name": "PP-OCRv5_server_det",
            "model_dir": None,
            "limit_side_len": 512,
            "limit_type": "max",
            "max_side_limit": 1024,
            "thresh": 0.3,
            "box_thresh": 0.6,
            "unclip_ratio": 1.5,
        },
        "TextRecognition": {
            "module_name": "text_recognition",
            "model_name": "PP-OCRv5_server_rec",
            "model_dir": None,
            "batch_size": 1,
            "score_thresh": 0.8,
        },
    },
}


def resolve_region_config_section(
    region_spec: dict[str, Any],
    section_name: str,
) -> dict[str, Any]:
    raw_value = region_spec.get(section_name, {})
    if not isinstance(raw_value, dict):
        return {}
    return dict(raw_value)


def resolve_region_ocr_config(region_spec: dict[str, Any]) -> dict[str, Any]:
    return resolve_region_config_section(region_spec, "ocr_config")


def resolve_ocr_min_confidence(config: dict[str, Any] | None) -> float:
    if not isinstance(config, dict):
        return 0.0
    raw = config.get("ocr_min_confidence", 0.0)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value))


def build_ocr_engine_config(config: dict[str, Any] | None) -> dict[str, Any]:
    base = copy.deepcopy(DEFAULT_PADDLEX_OCR_CONFIG)
    if not isinstance(config, dict):
        return base
    overrides = {key: value for key, value in config.items() if key != "ocr_min_confidence"}
    return deep_merge_config(base, overrides)


def build_ocr_engine_config_key(config: dict[str, Any]) -> str:
    return json.dumps(config, sort_keys=True, separators=(",", ":"))


def deep_merge_config(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            merged[key] = deep_merge_config(base_value, value)
            continue
        merged[key] = copy.deepcopy(value)
    return merged
