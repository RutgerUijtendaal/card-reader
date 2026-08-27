from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

import card_reader_core.services.catalog.service as catalog_service_module
import card_reader_core.services.classification_rules.service as classification_rule_service_module
from card_reader_core.models import (
    Card,
    CardClassificationRule,
    CardFactionAssignment,
    CardManaFamilyAssignment,
    CardRoleAssignment,
    Symbol,
    Tag,
    Type,
)
from card_reader_core.repositories.cards import set_card_mana_families
from card_reader_core.services.classification_rules import (
    ClassificationRuleService,
    ClassificationRuleUpdateConflictError,
    ensure_default_mana_family_classification_rules,
)
from card_reader_core.services.catalog import CatalogService


def staff_client(username: str = "classification-admin") -> Client:
    user = get_user_model().objects.create_user(
        username=username,
        password="password",
        is_staff=True,
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    return client


def test_rule_crud_is_staff_only_and_rejects_duplicates() -> None:
    tag = Tag.objects.create(key="boss-rule", label="Boss Rule")
    payload = {
        "card_pool": "evil",
        "target_kind": "role",
        "target_key": "boss",
        "source_kind": "tag",
        "source_id": tag.id,
        "enabled": True,
    }

    assert (
        Client(HTTP_HOST="localhost")
        .post(
            "/admin/classification-rules",
            data=payload,
            content_type="application/json",
        )
        .status_code
        == 403
    )

    client = staff_client()
    created = client.post(
        "/admin/classification-rules",
        data=payload,
        content_type="application/json",
    )
    assert created.status_code == 201
    rule_id = created.json()["id"]
    assert created.json()["source_key"] == "boss-rule"
    assert (
        client.post(
            "/admin/classification-rules",
            data=payload,
            content_type="application/json",
        ).status_code
        == 409
    )

    disabled = client.patch(
        f"/admin/classification-rules/{rule_id}",
        data={"enabled": False},
        content_type="application/json",
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert client.delete(f"/admin/classification-rules/{rule_id}").status_code == 204
    assert not CardClassificationRule.objects.filter(id=rule_id).exists()


def test_rule_update_rejects_a_stale_read_instead_of_overwriting_a_concurrent_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tag = Tag.objects.create(key="concurrent-rule", label="Concurrent Rule")
    service = ClassificationRuleService()
    rule = service.create_rule(
        card_pool="evil",
        target_kind="role",
        target_key="boss",
        source_kind="tag",
        source_id=tag.id,
    )
    stale_rule = CardClassificationRule.objects.select_related("tag").get(id=rule.id)
    service.update_rule(rule_id=rule.id, enabled=False)
    monkeypatch.setattr(
        classification_rule_service_module,
        "get_classification_rule",
        lambda _rule_id: stale_rule,
    )

    with pytest.raises(ClassificationRuleUpdateConflictError, match="Reload and retry"):
        service.update_rule(rule_id=rule.id, target_key="location")

    rule.refresh_from_db()
    assert rule.target_key == "boss"
    assert rule.enabled is False


def test_catalog_definitions_are_global_and_sources_have_reverse_references() -> None:
    tag = Tag.objects.create(key="location-rule", label="Location Rule")
    rule = ClassificationRuleService().create_rule(
        card_pool="evil",
        target_kind="role",
        target_key="location",
        source_kind="tag",
        source_id=tag.id,
    )
    active = Card.objects.create(
        key="linked-location",
        label="Linked Location",
        card_pool="evil",
    )
    CardRoleAssignment.objects.create(card=active, role="location")
    CardFactionAssignment.objects.create(card=active, faction="blood")
    set_card_mana_families(card=active, mana_families=("arcane", "dark"))
    deprecated = Card.objects.create(
        key="deprecated-location",
        label="Deprecated Location",
        card_pool="evil",
        lifecycle_status="deprecated",
    )
    CardRoleAssignment.objects.create(card=deprecated, role="location")
    CardFactionAssignment.objects.create(card=deprecated, faction="blood")
    Card.objects.create(
        key="deprecated-normal",
        label="Deprecated Normal",
        card_pool="evil",
        lifecycle_status="deprecated",
    )
    client = staff_client("classification-catalog-admin")

    catalog = client.get("/admin/catalog")
    assert catalog.status_code == 200
    roles = catalog.json()["classification"]["roles"]
    assert [row["label"] for row in roles] == [
        "Normal",
        "Hero",
        "Boss",
        "Location",
        "Boon",
        "Event",
        "Shop Item",
        "Directive",
        "Reminder",
        "Mana",
    ]
    location = next(row for row in roles if row["key"] == "location")
    assert location["rule_counts"]["evil"]["tag"] == 1
    assert location["rules"][0]["id"] == rule.id
    assert location["linked_card_counts"]["evil"] == 1
    normal = next(row for row in roles if row["key"] == "standard")
    assert normal["linked_card_counts"]["evil"] == 0
    assert [row["label"] for row in catalog.json()["classification"]["factions"]] == [
        "No faction",
        "Order",
        "Blood",
        "Dark",
        "Metal",
        "Fire",
    ]
    blood = next(
        row for row in catalog.json()["classification"]["factions"] if row["key"] == "blood"
    )
    no_faction = next(
        row
        for row in catalog.json()["classification"]["factions"]
        if row["key"] == "none"
    )
    assert blood["linked_card_counts"]["evil"] == 1
    assert no_faction["linked_card_counts"]["evil"] == 0
    mana_families = catalog.json()["classification"]["mana_families"]
    assert [row["label"] for row in mana_families] == [
        "Colorless",
        "Arcane",
        "Dark",
        "Divine",
        "Martial",
        "Occult",
        "Primal",
    ]
    arcane = next(row for row in mana_families if row["key"] == "arcane")
    assert arcane["linked_card_counts"]["evil"] == 1
    assert arcane["display_symbol_key"] == "arcane-mana"
    assert arcane["display_symbol"]["key"] == "arcane-mana"

    detail = client.get(f"/admin/tags/{tag.id}")
    assert detail.status_code == 200
    assert detail.json()["classification_rules"][0]["target_key"] == "location"


def test_rule_sources_are_protected_until_rules_are_removed() -> None:
    type_row = Type.objects.create(key="event-rule", label="Event Rule")
    rule = ClassificationRuleService().create_rule(
        card_pool="neutral",
        target_kind="role",
        target_key="event",
        source_kind="type",
        source_id=type_row.id,
    )
    client = staff_client("classification-protect-admin")

    blocked = client.delete(f"/admin/types/{type_row.id}")
    assert blocked.status_code == 409
    assert "Neutral" in blocked.json()["detail"] or "neutral" in blocked.json()["detail"]
    assert "event" in blocked.json()["detail"]

    ClassificationRuleService().delete_rule(rule_id=rule.id)
    assert client.delete(f"/admin/types/{type_row.id}").status_code == 204


def test_snapshots_are_pool_scoped_and_exclude_disabled_rules() -> None:
    tag = Tag.objects.create(key="shared-rule", label="Shared Rule")
    service = ClassificationRuleService()
    player = service.create_rule(
        card_pool="player",
        target_kind="role",
        target_key="hero",
        source_kind="tag",
        source_id=tag.id,
    )
    service.create_rule(
        card_pool="evil",
        target_kind="role",
        target_key="boss",
        source_kind="tag",
        source_id=tag.id,
    )
    disabled = service.create_rule(
        card_pool="player",
        target_kind="role",
        target_key="event",
        source_kind="tag",
        source_id=tag.id,
        enabled=False,
    )

    snapshot = service.build_snapshot(
        card_pool="player",
        include_roles=True,
        include_factions=True,
    )
    assert [rule["rule_id"] for rule in snapshot["rules"]] == [player.id]
    assert disabled.id not in {rule["rule_id"] for rule in snapshot["rules"]}


def test_dark_metal_and_fire_are_supported_faction_rule_targets() -> None:
    dark_tag = Tag.objects.get(key="dark")
    metal_tag = Tag.objects.get(key="metal")
    fire_tag = Tag.objects.get(key="fire")
    service = ClassificationRuleService()

    dark_rule = service.create_rule(
        card_pool="evil",
        target_kind="faction",
        target_key="dark",
        source_kind="tag",
        source_id=dark_tag.id,
    )
    metal_rule = service.create_rule(
        card_pool="evil",
        target_kind="faction",
        target_key="metal",
        source_kind="tag",
        source_id=metal_tag.id,
    )
    fire_rule = service.create_rule(
        card_pool="evil",
        target_kind="faction",
        target_key="fire",
        source_kind="tag",
        source_id=fire_tag.id,
    )

    assert [dark_rule.target_key, metal_rule.target_key, fire_rule.target_key] == [
        "dark",
        "metal",
        "fire",
    ]


def test_symbol_rules_support_all_classification_targets_and_protect_the_source() -> None:
    symbol = Symbol.objects.create(key="classification-source", label="Classification Source")
    service = ClassificationRuleService()
    rules = [
        service.create_rule(
            card_pool="player",
            target_kind=target_kind,
            target_key=target_key,
            source_kind="symbol",
            source_id=symbol.id,
        )
        for target_kind, target_key in (
            ("role", "hero"),
            ("faction", "order"),
            ("mana_family", "arcane"),
        )
    ]

    snapshot = service.build_snapshot(
        card_pool="player",
        include_roles=True,
        include_factions=True,
        include_mana_families=True,
    )
    assert {row["rule_id"] for row in snapshot["rules"]} == {rule.id for rule in rules}
    detail = staff_client("classification-symbol-admin").get(f"/admin/symbols/{symbol.id}")
    assert detail.status_code == 200
    assert {row["target_kind"] for row in detail.json()["classification_rules"]} == {
        "role",
        "faction",
        "mana_family",
    }
    assert staff_client("classification-symbol-delete-admin").delete(
        f"/admin/symbols/{symbol.id}"
    ).status_code == 409


def test_default_player_mana_symbol_rules_reconcile_idempotently_without_placeholders() -> None:
    Symbol.objects.exclude(key__in={"arcane-mana", "arcane-affinity"}).delete()

    assert ensure_default_mana_family_classification_rules() == 2
    assert ensure_default_mana_family_classification_rules() == 0
    assert set(
        CardClassificationRule.objects.filter(target_kind="mana_family").values_list(
            "target_key", "symbol__key"
        )
    ) == {
        ("arcane", "arcane-mana"),
        ("arcane", "arcane-affinity"),
    }
    assert not Symbol.objects.filter(key="primal-mana").exists()


def test_creating_a_symbol_only_reconciles_that_symbol_default() -> None:
    arcane_symbol, _created = Symbol.objects.get_or_create(
        key="arcane-mana",
        defaults={"label": "Arcane Mana", "symbol_type": "mana"},
    )
    ensure_default_mana_family_classification_rules(symbol_keys={arcane_symbol.key})
    CardClassificationRule.objects.filter(
        card_pool="player",
        target_kind="mana_family",
        target_key="arcane",
        source_kind="symbol",
        symbol=arcane_symbol,
    ).delete()

    CatalogService().create_symbol(
        key="unrelated-new-symbol",
        label="Unrelated New Symbol",
    )

    assert not CardClassificationRule.objects.filter(
        card_pool="player",
        target_kind="mana_family",
        target_key="arcane",
        source_kind="symbol",
        symbol=arcane_symbol,
    ).exists()
    assert (
        ensure_default_mana_family_classification_rules(
            symbol_keys={arcane_symbol.key}
        )
        == 1
    )


def test_symbol_creation_rolls_back_when_default_rule_seeding_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical_key = "primal-mana"
    CardClassificationRule.objects.filter(symbol__key=canonical_key).delete()
    Symbol.objects.filter(key=canonical_key).delete()

    def fail_rule_seeding(*, symbol_keys: set[str] | None = None) -> int:
        assert symbol_keys == {canonical_key}
        raise RuntimeError("rule seeding failed")

    monkeypatch.setattr(
        catalog_service_module,
        "ensure_default_mana_family_classification_rules",
        fail_rule_seeding,
    )

    with pytest.raises(RuntimeError, match="rule seeding failed"):
        CatalogService().create_symbol(
            key=canonical_key,
            label="Primal Mana",
            symbol_type="mana",
        )

    assert not Symbol.objects.filter(key=canonical_key).exists()


def test_renaming_a_symbol_to_a_canonical_key_reconciles_its_default_rule() -> None:
    canonical_symbol = Symbol.objects.get(key="arcane-mana")
    assert (
        Symbol.objects.filter(id=canonical_symbol.id).update(
            key="legacy-arcane-mana"
        )
        == 1
    )

    symbol = Symbol.objects.create(
        key="pending-arcane-symbol",
        label="Pending Arcane Symbol",
        symbol_type="mana",
    )

    updated = CatalogService().update_symbol(
        entry_id=symbol.id,
        key="arcane-mana",
    )

    assert updated is not None
    assert updated.key == "arcane-mana"
    assert CardClassificationRule.objects.filter(
        card_pool="player",
        target_kind="mana_family",
        target_key="arcane",
        source_kind="symbol",
        symbol_id=symbol.id,
        enabled=True,
    ).exists()


def test_renaming_between_canonical_symbol_keys_replaces_the_obsolete_family_rule() -> None:
    symbol = Symbol.objects.get(key="arcane-mana")
    ensure_default_mana_family_classification_rules(symbol_keys={symbol.key})

    updated = CatalogService().update_symbol(
        entry_id=symbol.id,
        key="dark-mana",
    )

    assert updated is not None
    assert updated.key == "dark-mana"
    assert set(
        CardClassificationRule.objects.filter(
            card_pool="player",
            target_kind="mana_family",
            source_kind="symbol",
            symbol_id=symbol.id,
        ).values_list("target_key", flat=True)
    ) == {"dark"}


def test_canonical_symbol_rename_rejects_unrelated_family_rules() -> None:
    symbol = Symbol.objects.get(key="arcane-mana")
    ensure_default_mana_family_classification_rules(symbol_keys={symbol.key})
    ClassificationRuleService().create_rule(
        card_pool="player",
        target_kind="mana_family",
        target_key="divine",
        source_kind="symbol",
        source_id=symbol.id,
    )

    with pytest.raises(
        ValueError,
        match="conflict with its canonical key.*divine",
    ):
        CatalogService().update_symbol(entry_id=symbol.id, key="dark-mana")

    symbol.refresh_from_db()
    assert symbol.key == "arcane-mana"
    assert set(
        CardClassificationRule.objects.filter(
            card_pool="player",
            target_kind="mana_family",
            source_kind="symbol",
            symbol_id=symbol.id,
        ).values_list("target_key", flat=True)
    ) == {"arcane", "divine"}


def test_symbol_rename_rolls_back_when_default_rule_reconciliation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical_symbol = Symbol.objects.get(key="arcane-mana")
    assert (
        Symbol.objects.filter(id=canonical_symbol.id).update(
            key="legacy-arcane-mana"
        )
        == 1
    )
    symbol = Symbol.objects.create(
        key="pending-arcane-symbol",
        label="Pending Arcane Symbol",
        symbol_type="mana",
    )

    def fail_rule_reconciliation(*, symbol: Symbol, previous_key: str) -> int:
        assert symbol.key == "arcane-mana"
        assert previous_key == "pending-arcane-symbol"
        raise RuntimeError("rule reconciliation failed")

    monkeypatch.setattr(
        catalog_service_module,
        "reconcile_mana_family_rules_for_symbol_rename",
        fail_rule_reconciliation,
    )

    with pytest.raises(RuntimeError, match="rule reconciliation failed"):
        CatalogService().update_symbol(entry_id=symbol.id, key="arcane-mana")

    symbol.refresh_from_db()
    assert symbol.key == "pending-arcane-symbol"


def test_card_mana_family_assignment_is_unique_and_updates_the_cached_sort_key() -> None:
    card = Card.objects.create(key="mana-assignment", label="Mana Assignment")

    assert set_card_mana_families(card=card, mana_families=("dark", "arcane")) == (
        "arcane",
        "dark",
    )
    card.refresh_from_db()
    assert card.mana_family_sort_key == 1
    assert list(
        CardManaFamilyAssignment.objects.filter(card=card).values_list(
            "mana_family", flat=True
        )
    ) == ["arcane", "dark"]

    set_card_mana_families(card=card, mana_families=())
    card.refresh_from_db()
    assert card.mana_family_sort_key == 63
    assert not CardManaFamilyAssignment.objects.filter(card=card).exists()

    with pytest.raises(ValueError, match="Invalid card mana family"):
        set_card_mana_families(card=card, mana_families=("colorless",))


def test_snapshot_detector_sources_survive_later_catalog_edits_and_deletion() -> None:
    tag = Tag.objects.create(
        key="frozen-hero",
        label="Frozen Hero",
        identifiers_json=["original hero term"],
    )
    service = ClassificationRuleService()
    rule = service.create_rule(
        card_pool="player",
        target_kind="role",
        target_key="hero",
        source_kind="tag",
        source_id=tag.id,
    )
    snapshot = service.build_snapshot(
        card_pool="player",
        include_roles=True,
        include_factions=True,
    )
    original_tag_id = tag.id

    tag.key = "renamed-hero"
    tag.label = "Renamed Hero"
    tag.identifiers_json = ["replacement term"]
    tag.save(update_fields=["key", "label", "identifiers_json"])
    service.delete_rule(rule_id=rule.id)
    tag.delete()

    frozen_tags, frozen_types, frozen_symbols = service.detector_sources_from_snapshot(
        snapshot,
        card_pool="player",
    )
    assert frozen_types == []
    assert frozen_symbols == []
    assert [(row.id, row.key, row.label, row.identifiers_json) for row in frozen_tags] == [
        (original_tag_id, "frozen-hero", "Frozen Hero", ["original hero term"])
    ]


@pytest.mark.parametrize(
    ("target_kind", "target_key"),
    [
        ("role", "unknown"),
        ("faction", "unknown"),
        ("unknown", "hero"),
    ],
)
def test_rule_service_rejects_unknown_targets(target_kind: str, target_key: str) -> None:
    tag = Tag.objects.create(key=f"invalid-{target_kind}-{target_key}", label="Invalid")
    with pytest.raises(ValueError):
        ClassificationRuleService().create_rule(
            card_pool="player",
            target_kind=target_kind,
            target_key=target_key,
            source_kind="tag",
            source_id=tag.id,
        )
