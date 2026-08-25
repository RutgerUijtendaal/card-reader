from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from card_reader_core.models import (
    CARD_ROLES,
    CARD_FACTIONS,
    DEPRECATED_CARD_LIFECYCLE_STATUS,
    Card,
    CardBack,
    CardFaction,
    CardPool,
    CardRoleAssignment,
    CardVersion,
    is_card_pool,
    is_card_lifecycle_status,
    now_utc,
)
from card_reader_core.metadata import MANA_FAMILY_BY_KEY

from ..card_groups import card_is_group_anchor
from ..helpers import infer_mana_value
from ..metadata import (
    render_rule_text_for_card_version,
    replace_card_version_keywords,
    replace_card_version_symbols,
    replace_card_version_tags,
    replace_card_version_types,
)
from .queries import get_card, get_latest_card_version
from .classification import set_card_mana_families
from .identity import change_card_identity
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
from .types import FieldSourcesPayload, ParsedSnapshotPayload
from .writes import apply_latest_version_identity


@dataclass
class _CardUpdateState:
    name_changed: bool = False
    symbol_links_changed: bool = False
    classification_changed: bool = False
    destination_card_pool: CardPool | None = None
    destination_card_factions: tuple[CardFaction, ...] | None = None


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
        state = _CardUpdateState()
        _unlock_field_sources(
            field_sources,
            unlock_fields=unlock_fields,
            unlock_metadata_groups=unlock_metadata_groups,
        )
        _restore_version_values(
            version,
            snapshot=snapshot,
            field_sources=field_sources,
            restore_fields=restore_fields,
            restore_metadata_groups=restore_metadata_groups,
            state=state,
        )
        _apply_version_updates(
            version,
            updates=updates,
            field_sources=field_sources,
            state=state,
        )
        _apply_classification_updates(card, updates=updates, state=state)
        _apply_card_attribute_updates(card, updates=updates)

        if state.symbol_links_changed:
            apply_manual_rule_text(version, version.rules_text_enriched)

        if state.name_changed or state.destination_card_pool is not None or state.destination_card_factions is not None:
            change_card_identity(
                card=card,
                label=version.name if state.name_changed else None,
                card_pool=state.destination_card_pool,
                card_factions=state.destination_card_factions,
            )
        _save_card_updates(card, updates=updates, state=state)

        version.mana_value = infer_mana_value(
            mana_cost=version.mana_cost,
            mana_symbols=version.mana_symbols_json,
        )
        version.field_sources_json = field_sources
        version.updated_at = now_utc()
        version.save()
        return card, version


def _unlock_field_sources(
    field_sources: FieldSourcesPayload,
    *,
    unlock_fields: list[str],
    unlock_metadata_groups: list[str],
) -> None:
    for field_name in unlock_fields:
        if field_name in field_sources["fields"]:
            field_sources["fields"][field_name] = FIELD_SOURCE_AUTO
    for group_name in unlock_metadata_groups:
        if group_name in field_sources["metadata"]:
            field_sources["metadata"][group_name] = FIELD_SOURCE_AUTO


def _restore_version_values(
    version: CardVersion,
    *,
    snapshot: ParsedSnapshotPayload,
    field_sources: FieldSourcesPayload,
    restore_fields: list[str],
    restore_metadata_groups: list[str],
    state: _CardUpdateState,
) -> None:
    for field_name in restore_fields:
        if field_name not in field_sources["fields"]:
            continue
        value = snapshot["fields"].get(field_name)
        if field_name == "rules_text":
            apply_manual_rule_text(version, value)
        else:
            apply_scalar_value(version, field_name, value)
        field_sources["fields"][field_name] = FIELD_SOURCE_AUTO
        if field_name == "name":
            state.name_changed = True

    for group_name in restore_metadata_groups:
        if group_name not in field_sources["metadata"]:
            continue
        restore_metadata_group_from_snapshot(version, group_name, snapshot)
        field_sources["metadata"][group_name] = FIELD_SOURCE_AUTO
        if group_name == "symbols":
            state.symbol_links_changed = True


def _apply_version_updates(
    version: CardVersion,
    *,
    updates: dict[str, object],
    field_sources: FieldSourcesPayload,
    state: _CardUpdateState,
) -> None:
    for field_name in SCALAR_FIELD_NAMES:
        if field_name not in updates:
            continue
        value = updates[field_name]
        if field_name == "rules_text":
            apply_manual_rule_text(version, value)
        else:
            apply_scalar_value(version, field_name, value)
        field_sources["fields"][field_name] = FIELD_SOURCE_MANUAL
        if field_name == "name":
            state.name_changed = True

    _apply_metadata_updates(
        version,
        updates=updates,
        field_sources=field_sources,
        state=state,
    )


def _apply_metadata_updates(
    version: CardVersion,
    *,
    updates: dict[str, object],
    field_sources: FieldSourcesPayload,
    state: _CardUpdateState,
) -> None:
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
        state.symbol_links_changed = True


def _apply_classification_updates(
    card: Card,
    *,
    updates: dict[str, object],
    state: _CardUpdateState,
) -> None:
    if "card_pool" in updates:
        state.destination_card_pool = _validated_card_pool(updates["card_pool"])
        state.classification_changed = True
    if "card_mana_families" in updates:
        mana_families = _validated_mana_families(updates["card_mana_families"])
        set_card_mana_families(card=card, mana_families=mana_families)
        state.classification_changed = True
    if "card_factions" in updates:
        state.destination_card_factions = _validated_card_factions(
            updates["card_factions"]
        )
        state.classification_changed = True
    if "card_roles" in updates:
        _replace_card_roles(card, updates["card_roles"])
        state.classification_changed = True


def _validated_card_pool(value: object) -> CardPool:
    card_pool = str(value)
    if not is_card_pool(card_pool):
        raise ValueError("Invalid card pool.")
    return card_pool


def _validated_mana_families(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("Card mana families must be a list.")
    mana_families = [str(item) for item in value]
    if any(item not in MANA_FAMILY_BY_KEY for item in mana_families):
        raise ValueError("Invalid card mana family.")
    return mana_families


def _validated_card_factions(value: object) -> tuple[CardFaction, ...]:
    if not isinstance(value, list):
        raise ValueError("Card factions must be a list.")
    requested_factions = {str(faction) for faction in value}
    if not requested_factions.issubset(CARD_FACTIONS):
        raise ValueError("Invalid card faction.")
    return tuple(faction for faction in CARD_FACTIONS if faction in requested_factions)


def _replace_card_roles(card: Card, value: object) -> None:
    if not isinstance(value, list):
        raise ValueError("Card roles must be a list.")
    requested_roles = {str(role) for role in value}
    if not requested_roles.issubset(CARD_ROLES):
        raise ValueError("Invalid card role.")

    assignments = CardRoleAssignment.objects.filter(card_id=card.id)
    assignments.exclude(role__in=requested_roles).delete()
    existing_roles = set(assignments.values_list("role", flat=True))
    missing_roles = requested_roles - existing_roles
    CardRoleAssignment.objects.bulk_create(
        [
            CardRoleAssignment(card=card, role=role)
            for role in CARD_ROLES
            if role in missing_roles
        ],
        ignore_conflicts=True,
    )
    prefetched_objects = getattr(card, "_prefetched_objects_cache", None)
    if prefetched_objects is not None:
        prefetched_objects.pop("role_assignments", None)


def _apply_card_attribute_updates(card: Card, *, updates: dict[str, object]) -> None:
    if "deck_building_config" in updates:
        card.deck_building_config_json = updates["deck_building_config"]
    if "lifecycle_status" in updates:
        card.lifecycle_status = _validated_lifecycle_status(
            card,
            updates["lifecycle_status"],
        )
    if "card_back_override" in updates:
        card.card_back_override = _validated_card_back_override(
            updates["card_back_override"]
        )


def _validated_lifecycle_status(card: Card, value: object) -> str:
    lifecycle_status = str(value)
    if not is_card_lifecycle_status(lifecycle_status):
        raise ValueError("Invalid card lifecycle status.")
    if lifecycle_status == DEPRECATED_CARD_LIFECYCLE_STATUS and card_is_group_anchor(card.id):
        raise ValueError("Card group anchors cannot be deprecated.")
    return lifecycle_status


def _validated_card_back_override(value: object) -> CardBack | None:
    if value is not None and not isinstance(value, CardBack):
        raise ValueError("Invalid card-back override.")
    return value


def _save_card_updates(
    card: Card,
    *,
    updates: dict[str, object],
    state: _CardUpdateState,
) -> None:
    direct_card_fields = {
        "deck_building_config": "deck_building_config_json",
        "lifecycle_status": "lifecycle_status",
        "card_back_override": "card_back_override",
    }
    update_fields = [
        model_field
        for update_key, model_field in direct_card_fields.items()
        if update_key in updates
    ]
    if not state.name_changed and not state.classification_changed and not update_fields:
        return
    card.updated_at = now_utc()
    card.save(update_fields=[*update_fields, "updated_at"])


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
    version.rules_text = render_rule_text_for_card_version(
        card_version_id=version.id,
        enriched_text=enriched_text,
    )
