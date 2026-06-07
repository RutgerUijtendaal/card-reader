from __future__ import annotations

from card_reader_core.models import CardVersion, CardVersionParseFlag, CardVersionParseFlagItem
from card_reader_core.repositories.metadata import (
    get_keywords_for_card_version,
    get_symbols_for_card_version,
    get_tags_for_card_version,
    get_types_for_card_version,
)
from card_reader_core.repositories.parse_flags import (
    ParseFlagItemInput,
    ParseFlagItemStatus,
    create_card_version_parse_flag,
    update_parse_flag_item_status,
)
from card_reader_core.services.notifications import NotificationService


def create_parse_flag_for_card_version(
    *,
    card_id: str,
    version_id: str,
    submitted_by_id: str,
    note: str,
    items: list[ParseFlagItemInput],
) -> CardVersionParseFlag | None:
    version = CardVersion.objects.filter(id=version_id, card_id=card_id).first()
    if version is None:
        return None
    return create_card_version_parse_flag(
        card_id=card_id,
        version_id=version_id,
        submitted_by_id=submitted_by_id,
        note=note,
        items=items,
        captured_values=_captured_values(version),
    )


def review_parse_flag_item(
    *,
    item_id: str,
    status: ParseFlagItemStatus,
    reviewed_by_id: str,
    review_note: str = "",
) -> CardVersionParseFlagItem | None:
    item = update_parse_flag_item_status(
        item_id=item_id,
        status=status,
        reviewed_by_id=reviewed_by_id,
        review_note=review_note,
    )
    if item is not None:
        NotificationService().notify_parse_flag_reviewed(item)
    return item


def _captured_values(version: CardVersion) -> dict[str, str]:
    return {
        "name": version.name,
        "type_line": version.type_line,
        "mana_cost": version.mana_cost,
        "attack": "" if version.attack is None else str(version.attack),
        "health": "" if version.health is None else str(version.health),
        "rules_text": version.rules_text_enriched or version.rules_text,
        "keywords": _labels([row.label for row in get_keywords_for_card_version(version.id)]),
        "tags": _labels([row.label for row in get_tags_for_card_version(version.id)]),
        "types": _labels([row.label for row in get_types_for_card_version(version.id)]),
        "symbols": _labels([row.label for row in get_symbols_for_card_version(version.id)]),
        "other": "",
    }


def _labels(values: list[str]) -> str:
    return ", ".join(sorted(values, key=lambda value: value.lower()))
