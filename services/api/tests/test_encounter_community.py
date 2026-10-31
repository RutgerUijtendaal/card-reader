from uuid import uuid4
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from card_reader_core.models import Card, CardRoleAssignment
from card_reader_core.repositories import encounters
from card_reader_core.services.encounters import EncounterActor, EncounterService
from card_reader_core.services.exports import TtsCardExportService


def viewer(*, staff=False):
    user = get_user_model().objects.create_user(username=str(uuid4()), is_staff=staff)
    client = Client()
    client.force_login(user)
    return user, client


def create(client, **fields):
    response = client.post(
        "/my/encounters", fields, content_type="application/json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    )
    assert response.status_code == 201, response.content
    return response.json()


def update(client, record, **fields):
    return client.patch(
        f"/my/encounters/{record['id']}",
        {"revision": record["revision"], **fields},
        content_type="application/json",
    )


def evil(*, boss=False):
    card = Card.objects.create(key=str(uuid4()), label="Community card", card_pool="evil")
    if boss:
        CardRoleAssignment.objects.create(card=card, role="boss")
    return card


def valid_fields():
    return dict(
        name="Community fight",
        boss_card_id=evil(boss=True).id,
        entries=[{"card_id": evil().id, "quantity": 20}],
    )


def test_community_owner_lifecycle_and_staff_management():
    owner, client = viewer()
    _, other = viewer()
    _, staff = viewer(staff=True)
    card = evil()
    record = create(
        client, sideboards=[{"name": "Reserve", "entries": [{"card_id": card.id, "quantity": 2}]}]
    )
    assert record["creator"]["id"] == str(owner.pk)
    assert record["can_edit"] and record["can_delete"] and not record["is_official"]
    assert client.get("/my/encounters").json()["count"] == 1
    assert other.get("/my/encounters").json()["count"] == 0
    assert staff.get("/my/encounters").json()["count"] == 0
    assert staff.get("/staff/encounters").json()["count"] == 1
    assert other.get(f"/my/encounters/{record['id']}").status_code == 404
    assert update(other, record, name="Stolen").status_code == 404
    assert other.delete(f"/my/encounters/{record['id']}", HTTP_IF_MATCH="1").status_code == 404
    assert client.get("/encounters/bosses").status_code == 200
    assert Client().get("/encounters/bosses").status_code == 403
    record = update(
        client,
        record,
        name="Owner edit",
        sideboards=[{**record["sideboards"][0], "name": "Renamed"}],
    ).json()
    assert record["sideboards"][0]["name"] == "Renamed"
    record = update(staff, record, description_markup="Staff edit").json()
    assert record["creator"]["id"] == str(owner.pk)
    assert (
        client.delete(
            f"/my/encounters/{record['id']}", HTTP_IF_MATCH=str(record["revision"])
        ).status_code
        == 204
    )


@pytest.mark.parametrize("visibility", ["private", "unlisted", "public"])
@pytest.mark.parametrize("valid", [False, True])
def test_visibility_and_export_authorization_matrix(visibility, valid):
    _, owner = viewer()
    _, other = viewer()
    _, staff = viewer(staff=True)
    fields = valid_fields() if valid else {}
    record = create(owner, visibility=visibility, **fields)
    url = f"/encounters/{record['id']}"
    for client, privileged in [(owner, True), (staff, True), (other, False), (Client(), False)]:
        response = client.get(url)
        can_view = privileged or (visibility != "private" and valid)
        assert response.status_code == (200 if can_view else 404)
        if can_view:
            assert response.json()["can_edit"] is privileged
        assert client.get("/encounters").json()["count"] == int(visibility == "public" and valid)
        # Authorization precedes requested-board validation; full validity is irrelevant.
        exported = client.get(url + "/exports/tts?sideboard_id=missing")
        assert exported.status_code == (409 if privileged or visibility != "private" else 404)


@pytest.mark.parametrize("value", [True, False])
def test_ordinary_clients_cannot_submit_official_status(value):
    _, owner = viewer()
    response = owner.post(
        "/my/encounters",
        {"is_official": value},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert response.status_code == 403
    record = create(owner)
    assert update(owner, record, is_official=value).status_code == 403
    assert not owner.get(f"/my/encounters/{record['id']}").json()["is_official"]


def test_endorsement_blocks_all_owner_mutations_and_unmarking_restores_access():
    _, owner = viewer()
    _, staff = viewer(staff=True)
    original = create(owner, **valid_fields())
    official = update(staff, original, is_official=True).json()
    assert official["can_edit"] and official["can_delete"]
    owner_view = owner.get(f"/encounters/{original['id']}").json()
    assert owner_view["is_official"] and not owner_view["can_edit"] and not owner_view["can_delete"]
    assert owner.get("/my/encounters?is_official=true").json()["count"] == 1
    mutations = [
        dict(name="Changed"),
        dict(visibility="public"),
        dict(factions=["fire"]),
        dict(boss_card_id=None),
        dict(entries=[]),
        dict(sideboards=[]),
    ]
    for fields in mutations:
        assert update(owner, original, **fields).status_code == 403
        assert update(owner, official, **fields).status_code == 403
    for revision in [original["revision"], official["revision"]]:
        assert (
            owner.delete(
                f"/my/encounters/{original['id']}", HTTP_IF_MATCH=str(revision)
            ).status_code
            == 403
        )
    community = update(staff, official, is_official=False).json()
    assert (
        community["creator"] == original["creator"]
        and community["visibility"] == original["visibility"]
    )
    assert update(owner, community, name="Restored").status_code == 200


def test_atomic_policy_rechecks_after_read_and_before_write():
    user, owner = viewer()
    _, staff = viewer(staff=True)
    saved = create(owner)
    stale = encounters.get_encounter(saved["id"])
    actor = EncounterActor(str(user.pk))
    update(staff, saved, is_official=True)
    # The caller's object still claims this is a community Encounter.
    assert stale is not None and actor.can_manage(stale)
    with pytest.raises(encounters.EncounterForbidden):
        EncounterService().update(stale, {"name": "Race overwrite"}, saved["revision"], actor=actor)
    with pytest.raises(encounters.EncounterForbidden):
        encounters.delete_encounter(
            saved["id"], saved["revision"], actor_id=str(user.pk), is_staff=False
        )
    assert encounters.get_encounter(saved["id"]).name == ""


def test_creation_receipt_survives_endorsement_and_deletion():
    _, owner = viewer()
    _, other = viewer()
    _, staff = viewer(staff=True)
    key = str(uuid4())
    response = owner.post(
        "/my/encounters", {}, content_type="application/json", HTTP_IDEMPOTENCY_KEY=key
    )
    original = response.json()
    endorsed = update(staff, original, is_official=True).json()
    replay = owner.post(
        "/my/encounters",
        {"entries": "invalid replay"},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert replay.status_code == 200 and replay.json()["id"] == original["id"]
    assert not replay.json()["can_edit"]
    lookup = f"/my/encounters/by-creation-key/{key}"
    assert not owner.get(lookup).json()["can_edit"]
    assert other.get(lookup).status_code == 404
    assert (
        staff.delete(
            f"/staff/encounters/{original['id']}", HTTP_IF_MATCH=str(endorsed["revision"])
        ).status_code
        == 204
    )
    assert owner.get(lookup).status_code == 410
    assert (
        owner.post(
            "/my/encounters", {}, content_type="application/json", HTTP_IDEMPOTENCY_KEY=key
        ).status_code
        == 410
    )


def test_official_filters_are_independent_of_visibility_name_and_factions():
    _, owner = viewer()
    _, staff = viewer(staff=True)
    community = create(owner, visibility="public", factions=["order"], **valid_fields())
    official = create(owner, visibility="public", factions=["order"], **valid_fields())
    update(staff, official, is_official=True)
    for client, path in [
        (Client(), "/encounters"),
        (owner, "/my/encounters"),
        (staff, "/staff/encounters"),
    ]:
        for value, expected in [("true", official), ("false", community)]:
            data = client.get(
                path, {"is_official": value, "q": "fight", "factions": ["order"]}
            ).json()
            assert [item["id"] for item in data["results"]] == [expected["id"]]
            assert "entries" not in data["results"][0]
        assert client.get(path, {"is_official": "nonsense"}).status_code == 400


def test_exports_validate_only_selected_board_with_incomplete_public_or_unlisted_records():
    _, owner = viewer()
    first, second = evil(), evil()
    record = create(
        owner,
        visibility="unlisted",
        boss_card_id=evil(boss=True).id,
        entries=[{"card_id": first.id, "quantity": 1}],
        sideboards=[
            {"name": "Good", "entries": [{"card_id": first.id, "quantity": 2}]},
            {"name": "Bad", "entries": [{"card_id": second.id, "quantity": 1}]},
        ],
    )
    second.lifecycle_status = "deprecated"
    second.save()
    saved = encounters.get_encounter(record["id"])
    # Capture selection after real board validation, before atlas/image preparation.
    service = TtsCardExportService()
    rows = [
        SimpleNamespace(version=SimpleNamespace(card=card))
        for card in [saved.boss_card, first, second]
    ]
    with (
        patch(
            "card_reader_core.services.exports.service.get_latest_card_list_rows_by_card_ids",
            return_value=rows,
        ),
        patch.object(service, "_build_export", side_effect=lambda selection: selection),
    ):
        main = service.build_encounter_export(saved)
        assert main.source_metadata["type"] == "encounter"
        good = service.build_encounter_export(saved, sideboard_id=record["sideboards"][0]["id"])
        assert good.source_metadata["sideboard_name"] == "Good"
        with pytest.raises(ValueError, match="deprecated"):
            service.build_encounter_export(saved, sideboard_id=record["sideboards"][1]["id"])
    no_boss = update(owner, record, boss_card_id=None).json()
    saved = encounters.get_encounter(no_boss["id"])
    with patch.object(service, "_build_export", side_effect=lambda selection: selection):
        service.build_encounter_export(saved, sideboard_id=record["sideboards"][0]["id"])
        with pytest.raises(ValueError, match="boss"):
            service.build_encounter_export(saved)
