from __future__ import annotations

from django.db import transaction

from card_reader_core.models import (
    DEPRECATED_CARD_LIFECYCLE_STATUS,
    Card,
    CardAlias,
    CardVersion,
    is_card_lifecycle_status,
    now_utc,
)
from card_reader_core.rules import render_enriched_rule_text
from card_reader_core.services.card_merges import ensure_card_alias

from ..card_groups import card_is_group_anchor
from ..helpers import infer_mana_value, normalize_slug_key
from ..metadata import (
    get_symbols_for_card_version,
    replace_card_version_keywords,
    replace_card_version_symbols,
    replace_card_version_tags,
    replace_card_version_types,
)
from .queries import get_card, get_latest_card_version
from .snapshots import (
    FIELD_SOURCE_AUTO,
    FIELD_SOURCE_MANUAL,
    SCALAR_FIELD_NAMES,
    apply_scalar_value,
    decode_field_sources,
    decode_parsed_snapshot,
    restore_metadata_group_from_snapshot,
    string_list,
)
from .writes import apply_latest_version_identity


def update_latest_card_version(
    *,
    card_id: str,
    updates: dict[str, object],
    restore_fields: list[str],
    restore_metadata_groups: list[str],
    unlock_fields: list[str],
    unlock_metadata_groups: list[str],
) -> tuple[Card, CardVersion] | None:
    card = get_card(card_id)
    version = get_latest_card_version(card_id)
    if card is None or version is None:
        return None

    snapshot = decode_parsed_snapshot(version.parsed_snapshot_json)
    field_sources = decode_field_sources(version.field_sources_json)

    with transaction.atomic():
        restored_name = False
        symbol_links_changed = False
        for field_name in unlock_fields:
            if field_name in field_sources["fields"]:
                field_sources["fields"][field_name] = FIELD_SOURCE_AUTO
        for group_name in unlock_metadata_groups:
            if group_name in field_sources["metadata"]:
                field_sources["metadata"][group_name] = FIELD_SOURCE_AUTO

        for field_name in restore_fields:
            if field_name not in field_sources["fields"]:
                continue
            if field_name == "rules_text":
                apply_manual_rule_text(version, snapshot["fields"].get(field_name))
            else:
                apply_scalar_value(version, field_name, snapshot["fields"].get(field_name))
            field_sources["fields"][field_name] = FIELD_SOURCE_AUTO
            if field_name == "name":
                restored_name = True
        for group_name in restore_metadata_groups:
            if group_name not in field_sources["metadata"]:
                continue
            restore_metadata_group_from_snapshot(version.id, group_name, snapshot)
            field_sources["metadata"][group_name] = FIELD_SOURCE_AUTO
            if group_name == "symbols":
                symbol_links_changed = True

        for field_name in SCALAR_FIELD_NAMES:
            if field_name not in updates:
                continue
            if field_name == "rules_text":
                apply_manual_rule_text(version, updates[field_name])
            else:
                apply_scalar_value(version, field_name, updates[field_name])
            field_sources["fields"][field_name] = FIELD_SOURCE_MANUAL
            if field_name == "name":
                restored_name = True

        if "keyword_ids" in updates:
            replace_card_version_keywords(
                card_version_id=version.id,
                keyword_ids=string_list(updates.get("keyword_ids")),
            )
            field_sources["metadata"]["keywords"] = FIELD_SOURCE_MANUAL
        if "tag_ids" in updates:
            replace_card_version_tags(
                card_version_id=version.id,
                tag_ids=string_list(updates.get("tag_ids")),
            )
            field_sources["metadata"]["tags"] = FIELD_SOURCE_MANUAL
        if "type_ids" in updates:
            replace_card_version_types(
                card_version_id=version.id,
                type_ids=string_list(updates.get("type_ids")),
            )
            field_sources["metadata"]["types"] = FIELD_SOURCE_MANUAL
        if "symbol_ids" in updates:
            replace_card_version_symbols(
                card_version_id=version.id,
                symbol_ids=string_list(updates.get("symbol_ids")),
            )
            field_sources["metadata"]["symbols"] = FIELD_SOURCE_MANUAL
            symbol_links_changed = True
        if "is_hero" in updates:
            card.is_hero = bool(updates["is_hero"])
        if "deck_building_config" in updates:
            card.deck_building_config_json = updates["deck_building_config"]
        if "lifecycle_status" in updates:
            lifecycle_status = str(updates["lifecycle_status"])
            if not is_card_lifecycle_status(lifecycle_status):
                raise ValueError("Invalid card lifecycle status.")
            if lifecycle_status == DEPRECATED_CARD_LIFECYCLE_STATUS and card_is_group_anchor(card.id):
                raise ValueError("Card group anchors cannot be deprecated.")
            card.lifecycle_status = lifecycle_status

        if symbol_links_changed:
            apply_manual_rule_text(version, version.rules_text_enriched)

        if restored_name or "name" in updates:
            next_key = normalize_slug_key(version.name)
            conflicting_card = Card.objects.filter(key=next_key).exclude(id=card.id).first()
            conflicting_alias = CardAlias.objects.filter(key=next_key).exclude(card_id=card.id).first()
            if conflicting_card is not None or conflicting_alias is not None:
                raise ValueError("Card name conflicts with another card or alias. Use card merge to resolve the duplicate.")
            ensure_card_alias(card=card, key=card.key, label=card.label)
            card.label = version.name
            card.key = next_key
        if (
            restored_name
            or "name" in updates
            or "is_hero" in updates
            or "deck_building_config" in updates
            or "lifecycle_status" in updates
        ):
            card.updated_at = now_utc()
            update_fields = ["updated_at"]
            if restored_name or "name" in updates:
                update_fields = ["label", "key", *update_fields]
            if "is_hero" in updates:
                update_fields = ["is_hero", *update_fields]
            if "deck_building_config" in updates:
                update_fields = ["deck_building_config_json", *update_fields]
            if "lifecycle_status" in updates:
                update_fields = ["lifecycle_status", *update_fields]
            card.save(update_fields=list(dict.fromkeys(update_fields)))

        version.mana_value = infer_mana_value(
            mana_cost=version.mana_cost,
            mana_symbols=version.mana_symbols_json,
        )
        version.field_sources_json = field_sources
        version.updated_at = now_utc()
        version.save()
        return card, version


def promote_card_version(
    *,
    card_id: str,
    version_id: str,
) -> tuple[Card, CardVersion] | None:
    card = get_card(card_id)
    version = (
        CardVersion.objects.select_related("card", "template", "previous_version", "parse_result")
        .filter(id=version_id, card_id=card.id if card is not None else card_id)
        .first()
    )
    if card is None or version is None:
        return None

    if version.is_latest and card.latest_version is not None and card.latest_version.id == version.id:
        return card, version

    with transaction.atomic():
        CardVersion.objects.filter(card_id=card.id, is_latest=True).exclude(id=version.id).update(
            is_latest=False,
            updated_at=now_utc(),
        )
        version.is_latest = True
        version.updated_at = now_utc()
        version.save(update_fields=["is_latest", "updated_at"])

        apply_latest_version_identity(card, version)
        return card, version


def apply_manual_rule_text(version: CardVersion, value: object) -> None:
    enriched_text = str(value or "")
    version.rules_text_enriched = enriched_text
    version.rules_text = render_enriched_rule_text(
        enriched_text,
        symbol_tokens_by_key={
            symbol.key: symbol.text_token
            for symbol in get_symbols_for_card_version(version.id)
        },
    )
