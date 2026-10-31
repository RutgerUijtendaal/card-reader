from __future__ import annotations

from uuid import uuid4
from unittest.mock import patch
import pytest

from django.contrib.auth import get_user_model
from django.test import Client
from django.db import connection
from django.test.utils import CaptureQueriesContext

from card_reader_core.models import Card, CardGroup, CardGroupMember, CardRoleAssignment
from card_reader_core.repositories.encounters import get_encounter
from card_reader_core.services.exports import TtsCardExportService


def staff_client() -> Client:
    user = get_user_model().objects.create_user(username=f"staff-{uuid4()}", is_staff=True)
    client = Client()
    client.force_login(user)
    return client


def card(*, boss: bool = False, pool: str = "evil") -> Card:
    value = Card.objects.create(key=str(uuid4()), label="Boss" if boss else "Card", card_pool=pool)
    if boss:
        CardRoleAssignment.objects.create(card=value, role="boss")
    return value


def create(client: Client, **fields: object):
    return client.post(
        "/staff/encounters",
        fields,
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )


def update(client: Client, saved: dict, **fields: object):
    return client.patch(
        f"/staff/encounters/{saved['id']}",
        {"revision": saved["revision"], **fields},
        content_type="application/json",
    )


def test_free_flow_drafts_shared_staff_and_public_validity():
    client, other, anonymous = staff_client(), staff_client(), Client()
    boss, normal = card(boss=True), card()
    response = create(client, entries=[{"card_id": normal.id, "quantity": 19}], visibility="public")
    assert response.status_code == 201
    draft = response.json()
    assert not draft["status"]["is_valid"]
    assert other.get(f"/staff/encounters/{draft['id']}").status_code == 200
    assert anonymous.get(f"/encounters/{draft['id']}").status_code == 404
    updated = update(other, draft, name="Night raid", boss_card_id=boss.id).json()
    assert not updated["status"]["is_valid"]  # Boss does not count toward the minimum.
    valid = update(client, updated, entries=[{"card_id": normal.id, "quantity": 20}]).json()
    assert valid["status"]["is_valid"]
    assert anonymous.get(f"/encounters/{draft['id']}").status_code == 200
    assert anonymous.get("/encounters").json()["count"] == 1
    normal.lifecycle_status = "deprecated"
    normal.save()
    assert anonymous.get("/encounters").json()["count"] == 0
    assert anonymous.get(f"/encounters/{draft['id']}/exports/tts").status_code == 404
    assert other.get(f"/staff/encounters/{draft['id']}").json()["entries"][0]["quantity"] == 20


def test_summary_query_count_does_not_grow_per_encounter():
    client = staff_client()
    create(client, boss_card_id=card(boss=True).id)
    with CaptureQueriesContext(connection) as single:
        assert client.get("/staff/encounters").json()["count"] == 1
    for _ in range(4):
        create(client, boss_card_id=card(boss=True).id)
    with CaptureQueriesContext(connection) as multiple:
        response = client.get("/staff/encounters")
        assert response.json()["count"] == 5
        assert all("entries" not in record for record in response.json()["results"])
    assert len(multiple) == len(single)


def test_encounter_detail_batches_version_metadata_and_preserves_duplicate_boss_entries():
    from card_reader_core.models import CardVersion, CardVersionSymbol, ContentVersion, Symbol, Template
    from card_reader_core.models.encounter import Encounter, EncounterEntry

    owner = get_user_model().objects.create_user(username="encounter-query-owner", is_staff=True)
    template = Template.objects.create(key="encounter-query-template", label="Query template")
    content = ContentVersion.objects.create(
        version_number="91.0.0", base_version="91.0.0", major=91, minor=0, patch=0,
        description="Query regression",
    )
    symbol = Symbol.objects.create(key="encounter-query-symbol", label="Query symbol")
    cards = [card(boss=index == 0) for index in range(25)]
    for value in cards:
        version = CardVersion.objects.create(
            card=value, template=template, image_hash=value.id,
            name=value.label, content_version=content,
        )
        CardVersionSymbol.objects.create(card_version=version, symbol=symbol)
        value.latest_version = version
        value.save(update_fields=["latest_version"])
    group = CardGroup.objects.create(key="encounter-query-group", anchor_card=cards[0])
    for position, value in enumerate(cards[:3]):
        CardGroupMember.objects.create(group=group, card=value, position=position)
    record = Encounter.objects.create(
        creator=owner, name="Query encounter", visibility="public",
        boss_card=cards[0], boss_group=group,
    )
    counts = []
    for batch in (cards[:5], cards[5:]):
        EncounterEntry.objects.bulk_create([
            EncounterEntry(encounter=record, card=value, quantity=4, position=cards.index(value))
            for value in batch
        ])
        with CaptureQueriesContext(connection) as queries:
            response = Client().get(f"/encounters/{record.id}")
        assert response.status_code == 200
        counts.append(len(queries))
        payload = response.json()
        assert [row["id"] for row in payload["boss_cards"]] == [value.id for value in cards[:3]]
        assert payload["entries"][0]["card_id"] == cards[0].id
        assert payload["entries"][0]["quantity"] == 4
        assert payload["boss_card"]["content_version"]["id"] == content.id
        assert payload["boss_card"]["symbols"][0]["id"] == symbol.id
    assert counts[0] == counts[1]
    assert counts[1] <= 40


def test_pool_restrictions_and_independent_faction_tags():
    client = staff_client()
    boss, normal, player = card(boss=True), card(), card(pool="player")
    assert create(client, entries=[{"card_id": player.id, "quantity": 1}]).status_code == 400
    response = create(
        client,
        boss_card_id=boss.id,
        factions=["fire", "order", "fire"],
        entries=[{"card_id": normal.id, "quantity": 50}],
    )
    assert response.status_code == 201
    saved = response.json()
    assert saved["factions"] == ["order", "fire"]
    assert update(client, saved, boss_card_id=card(boss=True).id).json()["factions"] == [
        "order",
        "fire",
    ]
    assert client.get("/staff/encounters?factions=fire").json()["count"] == 1
    assert client.get("/staff/encounters?factions=unknown").status_code == 400
    assert create(client, factions=["unknown"]).status_code == 400
    assert create(client, entries=[{"card_id": normal.id, "quantity": 0}]).status_code == 400


def test_idempotency_replay_before_validation_and_deleted_outcome():
    client = staff_client()
    key = str(uuid4())
    response = client.post(
        "/staff/encounters", {}, content_type="application/json", HTTP_IDEMPOTENCY_KEY=key
    )
    assert response.status_code == 201
    record = response.json()
    replay = client.post(
        "/staff/encounters",
        {"factions": ["invalid"]},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert replay.status_code == 200 and replay.json()["id"] == record["id"]
    assert (
        client.delete(
            f"/staff/encounters/{record['id']}", HTTP_IF_MATCH=str(record["revision"])
        ).status_code
        == 204
    )
    assert client.get(f"/staff/encounters/by-creation-key/{key}").status_code == 410
    assert (
        client.post(
            "/staff/encounters", {}, content_type="application/json", HTTP_IDEMPOTENCY_KEY=key
        ).status_code
        == 410
    )
    assert staff_client().get(f"/staff/encounters/by-creation-key/{key}").status_code == 404


def test_revision_conflicts_do_not_overwrite_or_delete():
    client = staff_client()
    saved = create(client, name="First").json()
    assert update(client, saved, name="Second").status_code == 200
    assert update(client, saved, name="Stale").status_code == 409
    assert (
        client.delete(
            f"/staff/encounters/{saved['id']}", HTTP_IF_MATCH=str(saved["revision"])
        ).status_code
        == 409
    )
    assert client.get(f"/staff/encounters/{saved['id']}").json()["name"] == "Second"


def test_nonstaff_cannot_write_or_inspect_private_records():
    record = create(staff_client()).json()
    for authenticated in (False, True):
        client = Client()
        if authenticated:
            client.force_login(get_user_model().objects.create_user(username=str(uuid4())))
        assert client.get("/staff/encounters").status_code in (401, 403)
        assert client.patch(
            f"/staff/encounters/{record['id']}", {}, content_type="application/json"
        ).status_code in (401, 403)
        assert client.get(f"/encounters/{record['id']}").status_code == 404
        assert client.get(f"/encounters/{record['id']}/exports/tts").status_code == 404


def test_boss_group_validation_tracks_current_membership():
    client = staff_client()
    boss, linked, normal = card(boss=True), card(), card()
    group = CardGroup.objects.create(key=str(uuid4()), name="Boss pair", anchor_card=boss)
    CardGroupMember.objects.create(group=group, card=boss, position=1)
    CardGroupMember.objects.create(group=group, card=linked, position=2)
    saved = create(
        client,
        name="Grouped",
        visibility="public",
        boss_card_id=boss.id,
        boss_group_id=group.id,
        entries=[{"card_id": normal.id, "quantity": 20}],
    ).json()
    assert saved["status"]["is_valid"]
    assert [value["id"] for value in saved["boss_cards"]] == [boss.id, linked.id]
    linked.card_pool = "neutral"
    linked.save()
    assert Client().get(f"/encounters/{saved['id']}").status_code == 404
    assert client.get(f"/encounters/{saved['id']}/exports/tts").status_code == 409
    assert update(client, saved, description_markup="Still editing").status_code == 200


def test_export_uses_boss_then_saved_quantities_and_order():
    # Exercise collection construction without filesystem/renderer work.
    from types import SimpleNamespace

    client = staff_client()
    boss, linked, normal = card(boss=True), card(), card()
    group = CardGroup.objects.create(key=str(uuid4()), anchor_card=boss)
    CardGroupMember.objects.create(group=group, card=boss, position=1)
    CardGroupMember.objects.create(group=group, card=linked, position=2)
    saved = create(
        client,
        boss_card_id=boss.id,
        boss_group_id=group.id,
        factions=["blood"],
        entries=[{"card_id": normal.id, "quantity": 7}, {"card_id": linked.id, "quantity": 2}],
    ).json()
    record = get_encounter(saved["id"])
    assert record is not None
    rows = [
        SimpleNamespace(version=SimpleNamespace(card=value)) for value in (boss, linked, normal)
    ]
    with (
        patch(
            "card_reader_core.services.exports.service.get_latest_card_list_rows_by_card_ids",
            return_value=rows,
        ),
        patch.object(TtsCardExportService, "_build_export") as build,
    ):
        TtsCardExportService().build_encounter_export(record)
    selection = build.call_args.args[0]
    assert [
        (entry.row.version.card.id, entry.quantity, entry.required) for entry in selection.entries
    ] == [(boss.id, 1, True), (linked.id, 1, True), (normal.id, 7, False), (linked.id, 2, False)]
    assert selection.source_metadata["type"] == "encounter"
    assert selection.source_metadata["factions"] == ["blood"]


@pytest.mark.parametrize("sort", ["default", "name_asc"])
def test_boss_picker_requires_group_primary_boss_and_keeps_standalones(sort):
    from card_reader_core.models import CardVersion, Template

    boss, primary, standalone = card(boss=True), card(), card(boss=True)
    for value in (boss, primary, standalone):
        version = CardVersion.objects.create(
            card=value,
            version_number=1,
            template=Template.objects.first(),
            name=value.label,
            image_hash=str(uuid4()),
        )
        value.latest_version = version
        value.save()
    group = CardGroup.objects.create(key=str(uuid4()), anchor_card=primary)
    CardGroupMember.objects.create(group=group, card=primary, position=0)
    CardGroupMember.objects.create(group=group, card=boss, position=1)
    response = staff_client().get(f"/staff/encounters/bosses?card_pool=player&sort={sort}")
    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert {item["id"] for item in response.json()["results"]} == {boss.id, standalone.id}
    group.anchor_card = boss
    group.save()
    grouped = staff_client().get(f"/staff/encounters/bosses?sort={sort}").json()
    assert grouped["count"] == 2
    assert any(
        item["result_type"] == "card_group" and item["anchor_card_id"] == boss.id
        for item in grouped["results"]
    )
    primary.card_pool = "neutral"
    primary.save()
    incompatible = staff_client().get(f"/staff/encounters/bosses?sort={sort}").json()
    assert incompatible["count"] == 2
    assert all(item["result_type"] == "card" for item in incompatible["results"])


def test_group_primary_changes_hide_public_encounter_and_referenced_group_cannot_be_deleted():
    client = staff_client()
    boss, linked = card(boss=True), card(boss=True)
    group = CardGroup.objects.create(key=str(uuid4()), anchor_card=boss)
    CardGroupMember.objects.create(group=group, card=boss, position=0)
    CardGroupMember.objects.create(group=group, card=linked, position=1)
    saved = create(
        client,
        name="Pair",
        visibility="public",
        boss_card_id=boss.id,
        boss_group_id=group.id,
        entries=[{"card_id": linked.id, "quantity": 20}],
    ).json()
    assert client.delete(f"/admin/card-groups/{group.id}").status_code == 409
    group.anchor_card = linked
    group.save()
    assert Client().get(f"/encounters/{saved['id']}").status_code == 404
    assert Client().get("/encounters").json()["count"] == 0
    detail = client.get(f"/staff/encounters/{saved['id']}").json()
    assert detail["boss_card"]["id"] == boss.id
    assert "primary card changed" in " ".join(detail["status"]["issues"])


def test_merge_preserves_encounter_quantities_boss_and_revision():
    from card_reader_core.services.card_merges import merge_cards

    client = staff_client()
    source, target = card(boss=True), card(boss=True)
    saved = create(
        client,
        boss_card_id=source.id,
        entries=[{"card_id": source.id, "quantity": 9}, {"card_id": target.id, "quantity": 11}],
    ).json()
    merge_cards(target_card_id=target.id, source_card_ids=[source.id])
    result = client.get(f"/staff/encounters/{saved['id']}").json()
    assert result["boss_card_id"] == target.id
    assert [(entry["card_id"], entry["quantity"]) for entry in result["entries"]] == [
        (target.id, 20)
    ]
    assert result["revision"] == saved["revision"] + 1
    assert update(client, saved, name="Stale").status_code == 409


def test_real_tts_payload_evil_sheets_boss_requirements_and_skipped_entries():
    from test_tts_card_sheets import _create_sheet_card
    from test_exports import _create_current_card_back, _decode_tts_card_export
    from card_reader_core.models import CardBackPoolDefault

    client = staff_client()
    boss = _create_sheet_card("Encounter boss", color=(10, 20, 30), card_pool="evil")
    linked = _create_sheet_card("Encounter linked", color=(50, 60, 70), card_pool="evil")
    CardRoleAssignment.objects.create(card=boss, role="boss")
    missing = card()
    _create_current_card_back("encounter")
    group = CardGroup.objects.create(key=str(uuid4()), anchor_card=boss)
    CardGroupMember.objects.create(group=group, card=boss, position=0)
    CardGroupMember.objects.create(group=group, card=linked, position=1)
    saved = create(
        client,
        boss_card_id=boss.id,
        boss_group_id=group.id,
        factions=["dark"],
        entries=[{"card_id": linked.id, "quantity": 2}, {"card_id": missing.id, "quantity": 3}],
    ).json()
    url = f"/encounters/{saved['id']}/exports/tts"
    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["exported_count"] == 4
    assert response.json()["skipped_count"] == 3
    payload = _decode_tts_card_export(response.json()["encoded_payload"])
    assert payload["schema"] == "card-reader.tts-cards.v3"
    assert payload["collection"]["source"]["boss_group_id"] == group.id
    assert [(entry["card_id"], entry["quantity"], entry["role"]) for entry in payload["cards"]] == [
        (boss.id, 1, "boss"),
        (linked.id, 1, "boss"),
        (linked.id, 2, "mainboard"),
    ]
    assert Client().get(url).status_code == 404  # Staff can test unfinished/private records.
    CardBackPoolDefault.objects.filter(card_pool="evil").delete()
    assert client.get(url).status_code == 409
    _create_current_card_back("encounter-restored")
    linked.latest_version.images.all().delete()
    assert client.get(url).status_code == 409  # A linked boss image is required, never skipped.


def test_reclassified_entries_stay_editable_but_cannot_be_increased():
    client = staff_client()
    normal = card()
    saved = create(client, entries=[{"card_id": normal.id, "quantity": 20}]).json()
    normal.card_pool = "player"
    normal.save()
    retained = update(
        client, saved, name="Keep editing", entries=[{"card_id": normal.id, "quantity": 20}]
    )
    assert retained.status_code == 200
    assert not retained.json()["status"]["is_valid"]
    assert (
        update(
            client, retained.json(), entries=[{"card_id": normal.id, "quantity": 21}]
        ).status_code
        == 400
    )
