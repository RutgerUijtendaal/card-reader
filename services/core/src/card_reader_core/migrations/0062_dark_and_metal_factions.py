from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from typing import Any

from django.db import migrations, models


OLD_DARK_FACTION = "darkness"
DARK_FACTION = "dark"
METAL_FACTION = "metal"
NON_TERMINAL_IMPORT_STATUSES = ("queued", "running", "canceling")
FACTION_LIST_KEYS = frozenset(
    {
        "card_factions",
        "override_factions",
        "resolved_factions",
    }
)


def _rewrite_faction_list(value: object, *, source: str, target: str) -> object:
    if not isinstance(value, list):
        return value
    return [target if item == source else item for item in value]


def _rewrite_json_payload(
    value: object,
    *,
    source: str,
    target: str,
    old_digest: str | None = None,
    new_digest: str | None = None,
) -> object:
    if isinstance(value, list):
        return [
            _rewrite_json_payload(
                item,
                source=source,
                target=target,
                old_digest=old_digest,
                new_digest=new_digest,
            )
            for item in value
        ]
    if not isinstance(value, dict):
        return value

    rewritten: dict[object, object] = {}
    target_kind = value.get("target_kind")
    for key, item in value.items():
        if key in FACTION_LIST_KEYS:
            rewritten[key] = _rewrite_faction_list(item, source=source, target=target)
        elif key == "target_key" and target_kind == "faction" and item == source:
            rewritten[key] = target
        elif (
            key == "snapshot_digest"
            and old_digest is not None
            and new_digest is not None
            and item == old_digest
        ):
            rewritten[key] = new_digest
        else:
            rewritten[key] = _rewrite_json_payload(
                item,
                source=source,
                target=target,
                old_digest=old_digest,
                new_digest=new_digest,
            )
    return rewritten


def _snapshot_digest(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _rewrite_rule_snapshot(
    value: object,
    *,
    source: str,
    target: str,
) -> tuple[object, str | None, str | None]:
    if not isinstance(value, dict):
        return value, None, None
    rewritten = _rewrite_json_payload(value, source=source, target=target)
    if rewritten == value or not isinstance(rewritten, dict):
        return value, None, None
    if not {"schema_version", "card_pool", "rules"}.issubset(rewritten):
        raise RuntimeError("Cannot migrate a malformed classification rule snapshot.")
    old_digest = value.get("digest") if isinstance(value.get("digest"), str) else None
    body = {
        "schema_version": rewritten["schema_version"],
        "card_pool": rewritten["card_pool"],
        "rules": rewritten["rules"],
    }
    new_digest = _snapshot_digest(body)
    rewritten["digest"] = new_digest
    return rewritten, old_digest, new_digest


def _preflight_non_terminal_imports(apps: Any) -> None:
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    job_ids = list(
        ImportJob.objects.filter(status__in=NON_TERMINAL_IMPORT_STATUSES)
        .order_by("created_at")
        .values_list("id", flat=True)[:10]
    )
    if job_ids:
        raise RuntimeError(
            "Card factions cannot be renamed while import jobs are non-terminal. "
            "Finish, cancel, or reset these jobs first: "
            + ", ".join(str(job_id) for job_id in job_ids)
        )


def _identity_updates(
    apps: Any,
    *,
    source: str,
    target: str,
    canonical_factions: tuple[str, ...],
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")
    CardFactionAssignment = apps.get_model("card_reader_core", "CardFactionAssignment")

    assignments_by_card: dict[str, list[str]] = defaultdict(list)
    for card_id, faction in CardFactionAssignment.objects.values_list("card_id", "faction"):
        assignments_by_card[str(card_id)].append(target if faction == source else str(faction))

    identity_by_card: dict[str, str] = {}
    seen_identities: dict[tuple[str, str, str], str] = {}
    for card in Card.objects.order_by("id"):
        requested = set(assignments_by_card.get(str(card.id), []))
        unsupported = requested.difference(canonical_factions)
        if unsupported:
            raise RuntimeError(
                "Cannot migrate card factions with unsupported assignments: "
                + ", ".join(sorted(unsupported))
            )
        faction_key = json.dumps(
            [faction for faction in canonical_factions if faction in requested],
            separators=(",", ":"),
        )
        identity_by_card[str(card.id)] = faction_key
        identity = (str(card.card_pool), faction_key, str(card.key))
        if identity in seen_identities:
            raise RuntimeError("Card faction rename would create a duplicate card identity.")
        seen_identities[identity] = f"card:{card.id}"

    alias_updates: list[tuple[str, str]] = []
    for alias in CardAlias.objects.order_by("id"):
        faction_key = identity_by_card[str(alias.card_id)]
        identity = (str(alias.card_pool), faction_key, str(alias.key))
        if identity in seen_identities:
            raise RuntimeError("Card faction rename would create a duplicate card or alias identity.")
        seen_identities[identity] = f"alias:{alias.id}"
        alias_updates.append((str(alias.id), faction_key))
    return identity_by_card, alias_updates


def _payload_uses_faction(value: object, faction: str) -> bool:
    if isinstance(value, list) and faction in value:
        return True
    return _rewrite_json_payload(value, source=faction, target="__removed_faction__") != value


def _guard_reverse_without_metal(apps: Any) -> None:
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")
    CardClassificationRule = apps.get_model("card_reader_core", "CardClassificationRule")
    CardFactionAssignment = apps.get_model("card_reader_core", "CardFactionAssignment")
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")

    has_metal = CardFactionAssignment.objects.filter(faction=METAL_FACTION).exists()
    has_metal = has_metal or CardClassificationRule.objects.filter(
        target_kind="faction", target_key=METAL_FACTION
    ).exists()
    for model in (Card, CardAlias):
        if any(
            METAL_FACTION in json.loads(value)
            for value in model.objects.values_list("faction_identity_key", flat=True)
        ):
            has_metal = True
    for job in ImportJob.objects.iterator():
        if _payload_uses_faction(job.card_faction_override_json, METAL_FACTION) or _payload_uses_faction(
            job.classification_rule_snapshot_json, METAL_FACTION
        ):
            has_metal = True
    for item in ImportJobItem.objects.iterator():
        if any(
            _payload_uses_faction(value, METAL_FACTION)
            for value in (
                item.resolved_card_factions_json,
                item.target_card_factions_snapshot_json,
                item.classification_inference_json,
                item.warnings_json,
            )
        ):
            has_metal = True
    if has_metal:
        raise RuntimeError("Migration 0062 cannot be reversed while Metal faction data exists.")


def _rewrite_factions(
    apps: Any,
    *,
    source: str,
    target: str,
    canonical_factions: tuple[str, ...],
) -> None:
    Card = apps.get_model("card_reader_core", "Card")
    CardAlias = apps.get_model("card_reader_core", "CardAlias")
    CardClassificationRule = apps.get_model("card_reader_core", "CardClassificationRule")
    CardFactionAssignment = apps.get_model("card_reader_core", "CardFactionAssignment")
    ImportJob = apps.get_model("card_reader_core", "ImportJob")
    ImportJobItem = apps.get_model("card_reader_core", "ImportJobItem")

    _preflight_non_terminal_imports(apps)
    if CardFactionAssignment.objects.filter(faction=target).exists():
        raise RuntimeError(f"Cannot rename {source} faction while {target} assignments already exist.")
    if CardClassificationRule.objects.filter(target_kind="faction", target_key=target).exists():
        raise RuntimeError(f"Cannot rename {source} faction while {target} rules already exist.")

    identity_by_card, alias_updates = _identity_updates(
        apps,
        source=source,
        target=target,
        canonical_factions=canonical_factions,
    )
    CardFactionAssignment.objects.filter(faction=source).update(faction=target)
    for card_id, faction_key in identity_by_card.items():
        Card.objects.filter(id=card_id).update(faction_identity_key=faction_key)
    for alias_id, faction_key in alias_updates:
        CardAlias.objects.filter(id=alias_id).update(faction_identity_key=faction_key)
    CardClassificationRule.objects.filter(target_kind="faction", target_key=source).update(
        target_key=target
    )

    digest_changes: dict[str, tuple[str | None, str | None]] = {}
    for job in ImportJob.objects.iterator():
        override = _rewrite_faction_list(job.card_faction_override_json, source=source, target=target)
        snapshot, old_digest, new_digest = _rewrite_rule_snapshot(
            job.classification_rule_snapshot_json,
            source=source,
            target=target,
        )
        digest_changes[str(job.id)] = (old_digest, new_digest)
        updates: dict[str, object] = {}
        if override != job.card_faction_override_json:
            updates["card_faction_override_json"] = override
        if snapshot != job.classification_rule_snapshot_json:
            updates["classification_rule_snapshot_json"] = snapshot
        if updates:
            ImportJob.objects.filter(id=job.id).update(**updates)

    for item in ImportJobItem.objects.iterator():
        old_digest, new_digest = digest_changes.get(str(item.job_id), (None, None))
        updates = {}
        faction_list_fields = {
            "resolved_card_factions_json",
            "target_card_factions_snapshot_json",
        }
        for field_name in (
            "resolved_card_factions_json",
            "target_card_factions_snapshot_json",
            "classification_inference_json",
            "warnings_json",
        ):
            current = getattr(item, field_name)
            if field_name in faction_list_fields:
                rewritten = _rewrite_faction_list(current, source=source, target=target)
            else:
                rewritten = _rewrite_json_payload(
                    current,
                    source=source,
                    target=target,
                    old_digest=old_digest,
                    new_digest=new_digest,
                )
            if rewritten != current:
                updates[field_name] = rewritten
        if updates:
            ImportJobItem.objects.filter(id=item.id).update(**updates)


def rename_darkness_to_dark(apps: Any, _schema_editor: Any) -> None:
    _rewrite_factions(
        apps,
        source=OLD_DARK_FACTION,
        target=DARK_FACTION,
        canonical_factions=("order", "blood", "dark", "metal"),
    )


def rename_dark_to_darkness(apps: Any, _schema_editor: Any) -> None:
    _guard_reverse_without_metal(apps)
    _rewrite_factions(
        apps,
        source=DARK_FACTION,
        target=OLD_DARK_FACTION,
        canonical_factions=("order", "blood", "darkness"),
    )


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0061_admin_owned_classification_rules")]

    operations = [
        migrations.RunPython(rename_darkness_to_dark, rename_dark_to_darkness),
        migrations.AlterField(
            model_name="cardfactionassignment",
            name="faction",
            field=models.CharField(
                choices=[
                    ("order", "Order"),
                    ("blood", "Blood"),
                    ("dark", "Dark"),
                    ("metal", "Metal"),
                ],
                db_index=True,
                max_length=64,
            ),
        ),
    ]
