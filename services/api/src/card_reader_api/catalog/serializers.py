from __future__ import annotations

from card_reader_core.models import Keyword, Symbol, Tag, Type


CatalogOption = Keyword | Tag | Type


def _catalog_option_payload(row: CatalogOption) -> dict[str, object]:
    return {
        "id": row.id,
        "key": row.key,
        "label": row.label,
    }


def keyword_payload(row: Keyword) -> dict[str, object]:
    return _catalog_option_payload(row)


def tag_payload(row: Tag) -> dict[str, object]:
    return _catalog_option_payload(row)


def type_payload(row: Type) -> dict[str, object]:
    return _catalog_option_payload(row)


def symbol_payload(row: Symbol) -> dict[str, object]:
    return {
        "id": row.id,
        "key": row.key,
        "label": row.label,
        "symbol_type": row.symbol_type,
        "detector_type": row.detector_type,
        "detection_config_json": row.detection_config_json,
        "reference_assets_json": row.reference_assets_json,
        "text_token": row.text_token,
        "enabled": row.enabled,
    }
