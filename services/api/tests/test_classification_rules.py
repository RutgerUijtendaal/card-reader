from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from card_reader_core.models import Card, CardClassificationRule, Tag, Type
from card_reader_core.services.classification_rules import ClassificationRuleService


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


def test_catalog_definitions_are_global_and_sources_have_reverse_references() -> None:
    tag = Tag.objects.create(key="location-rule", label="Location Rule")
    rule = ClassificationRuleService().create_rule(
        card_pool="evil",
        target_kind="role",
        target_key="location",
        source_kind="tag",
        source_id=tag.id,
    )
    Card.objects.create(
        key="linked-location",
        label="Linked Location",
        card_pool="evil",
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
    ]
    location = next(row for row in roles if row["key"] == "location")
    assert location["rule_counts"]["evil"]["tag"] == 1
    assert location["rules"][0]["id"] == rule.id
    assert [row["label"] for row in catalog.json()["classification"]["factions"]] == [
        "No faction",
        "Order",
        "Blood",
        "Dark",
        "Metal",
    ]

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


def test_dark_and_metal_are_supported_faction_rule_targets() -> None:
    dark_tag = Tag.objects.create(key="dark", label="Dark")
    metal_tag = Tag.objects.create(key="metal", label="Metal")
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

    assert [dark_rule.target_key, metal_rule.target_key] == ["dark", "metal"]


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

    frozen_tags, frozen_types = service.detector_sources_from_snapshot(
        snapshot,
        card_pool="player",
    )
    assert frozen_types == []
    assert [(row.id, row.key, row.label, row.identifiers_json) for row in frozen_tags] == [
        (original_tag_id, "frozen-hero", "Frozen Hero", ["original hero term"])
    ]


@pytest.mark.parametrize(
    ("target_kind", "target_key"),
    [
        ("role", "unknown"),
        ("faction", "darkness"),
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
