from __future__ import annotations

from django.db import transaction

from card_reader_core.models import (
    CARD_ROLES,
    CARD_FACTIONS,
    DEPRECATED_CARD_LIFECYCLE_STATUS,
    Card,
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
            restore_metadata_group_from_snapshot(version, group_name, snapshot)
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
        classification_changed = False
        destination_card_pool: CardPool | None = None
        destination_card_factions: tuple[CardFaction, ...] | None = None
        if "card_pool" in updates:
            card_pool = str(updates["card_pool"])
            if not is_card_pool(card_pool):
                raise ValueError("Invalid card pool.")
            destination_card_pool = card_pool
            classification_changed = True
        if "card_mana_families" in updates:
            raw_mana_families = updates["card_mana_families"]
            if not isinstance(raw_mana_families, list):
                raise ValueError("Card mana families must be a list.")
            requested_mana_families = [str(value) for value in raw_mana_families]
            if any(value not in MANA_FAMILY_BY_KEY for value in requested_mana_families):
                raise ValueError("Invalid card mana family.")
            set_card_mana_families(
                card=card,
                mana_families=requested_mana_families,
            )
            classification_changed = True
        if "card_factions" in updates:
            raw_factions = updates["card_factions"]
            if not isinstance(raw_factions, list):
                raise ValueError("Card factions must be a list.")
            requested_factions = {str(faction) for faction in raw_factions}
            if not requested_factions.issubset(CARD_FACTIONS):
                raise ValueError("Invalid card faction.")
            destination_card_factions = tuple(
                faction for faction in CARD_FACTIONS if faction in requested_factions
            )
            classification_changed = True
        if "card_roles" in updates:
            raw_roles = updates["card_roles"]
            if not isinstance(raw_roles, list):
                raise ValueError("Card roles must be a list.")
            requested_roles = {str(role) for role in raw_roles}
            if not requested_roles.issubset(CARD_ROLES):
                raise ValueError("Invalid card role.")
            CardRoleAssignment.objects.filter(card_id=card.id).exclude(role__in=requested_roles).delete()
            existing_roles = set(
                CardRoleAssignment.objects.filter(card_id=card.id).values_list("role", flat=True)
            )
            CardRoleAssignment.objects.bulk_create(
                [CardRoleAssignment(card=card, role=role) for role in CARD_ROLES if role in requested_roles - existing_roles],
                ignore_conflicts=True,
            )
            prefetched_objects = getattr(card, "_prefetched_objects_cache", None)
            if prefetched_objects is not None:
                prefetched_objects.pop("role_assignments", None)
            classification_changed = True
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

        identity_changed = (
            restored_name
            or "name" in updates
            or "card_pool" in updates
            or "card_factions" in updates
        )
        if identity_changed:
            change_card_identity(
                card=card,
                label=version.name if restored_name or "name" in updates else None,
                card_pool=destination_card_pool,
                card_factions=destination_card_factions,
            )
        if (
            restored_name
            or "name" in updates
            or classification_changed
            or "deck_building_config" in updates
            or "lifecycle_status" in updates
        ):
            card.updated_at = now_utc()
            update_fields = ["updated_at"]
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
    version.rules_text = render_rule_text_for_card_version(
        card_version_id=version.id,
        enriched_text=enriched_text,
    )
