from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, override_settings

from card_reader_core.models import CardVersion, ImportJob, ImportJobItem, ParseResult, Template, UserNotification
from card_reader_core.services.cards import (
    promote_card_version_with_notifications,
    save_parsed_card_with_notifications,
    update_latest_card_version_with_notifications,
)
from card_reader_core.repositories.notifications import NotificationInput, create_or_coalesce_notification
from card_reader_core.services.decks import DeckEntryInput, DeckService, DeckSideboardInput
from card_reader_core.storage import resolve_storage_path
from test_decks import _create_card
from test_parse_flags import _create_card_version


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_notification_api_lists_and_updates_current_user_notifications() -> None:
    _clear_notifications()
    user = _create_user("notification-owner", "password")
    other_user = _create_user("notification-other", "password")
    first = create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(user.pk),
            actor_id=str(other_user.pk),
            event_type="test.event",
            subject_type="test",
            subject_id="one",
            target_url="/cards/card-1",
            title="First notification",
            message="First message",
            metadata={"rank": 1},
            dedupe_key="test:event:one",
        )
    )
    create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(other_user.pk),
            event_type="test.event",
            subject_type="test",
            subject_id="other",
            target_url="/cards/card-2",
            title="Other user notification",
            message="Hidden",
            metadata={},
        )
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)

    summary_response = client.get("/notifications/summary")
    list_response = client.get("/notifications?status=unread")
    update_response = client.patch(
        f"/notifications/{first.id}",
        data={"read": True},
        content_type="application/json",
    )
    read_response = client.get("/notifications?status=read")

    assert summary_response.status_code == 200
    assert summary_response.json()["unread_count"] == 1
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["results"][0]["title"] == "First notification"
    assert list_response.json()["results"][0]["actor"]["username"] == "notification-other"
    assert update_response.status_code == 200
    assert update_response.json()["read_at"] is not None
    assert read_response.status_code == 200
    assert read_response.json()["count"] == 1


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_notifications_coalesce_and_mark_all_read() -> None:
    _clear_notifications()
    user = _create_user("notification-coalesce", "password")
    data = NotificationInput(
        recipient_id=str(user.pk),
        event_type="deck.card_changed",
        subject_type="deck_card",
        subject_id="deck-1:card-1",
        target_url="/my/decks/deck-1",
        title="Card changed in deck",
        message="First update",
        metadata={"version": 1},
        dedupe_key="deck.card_changed:deck-1:card-1",
    )
    first = create_or_coalesce_notification(data)
    second = create_or_coalesce_notification(
        NotificationInput(
            **{
                **data.__dict__,
                "message": "Second update",
                "metadata": {"version": 2},
            }
        )
    )
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    mark_response = client.post("/notifications/mark-all-read")

    assert first.id == second.id
    second.refresh_from_db()
    assert second.event_count == 2
    assert second.message == "Second update"
    assert second.metadata_json == {"version": 2}
    assert mark_response.status_code == 200
    assert mark_response.json()["updated_count"] == 1
    assert client.get("/notifications/summary").json()["unread_count"] == 0


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_notification_coalesce_retry_preserves_outer_transaction(monkeypatch) -> None:
    _clear_notifications()
    user = _create_user("notification-race-user", "password")
    data = NotificationInput(
        recipient_id=str(user.pk),
        event_type="deck.card_changed",
        subject_type="deck_card",
        subject_id="deck-1:card-1",
        target_url="/my/decks/deck-1",
        title="Card changed in deck",
        message="First update",
        metadata={"version": 1},
        dedupe_key="deck.card_changed:race",
    )
    existing = create_or_coalesce_notification(data)

    from card_reader_core.repositories.notifications import writes

    original_queryset = writes._active_dedupe_queryset
    original_create = writes._create_notification
    state = {"query_count": 0, "raised": False}

    def race_queryset(input_data: NotificationInput):
        state["query_count"] += 1
        queryset = original_queryset(input_data)
        if state["query_count"] == 1:
            return queryset.none()
        return queryset

    def race_create(input_data: NotificationInput):
        if not state["raised"]:
            state["raised"] = True
            raise IntegrityError("duplicate active dedupe")
        return original_create(input_data)

    monkeypatch.setattr(writes, "_active_dedupe_queryset", race_queryset)
    monkeypatch.setattr(writes, "_create_notification", race_create)

    with transaction.atomic():
        updated = create_or_coalesce_notification(
            NotificationInput(
                **{
                    **data.__dict__,
                    "message": "Race update",
                    "metadata": {"version": 2},
                }
            )
        )
        assert UserNotification.objects.filter(id=existing.id).exists()

    assert updated.id == existing.id
    updated.refresh_from_db()
    assert updated.event_count == 2
    assert updated.message == "Race update"


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_marking_read_deduped_notification_unread_conflicts_with_active_unread() -> None:
    _clear_notifications()
    user = _create_user("notification-unread-conflict", "password")
    data = NotificationInput(
        recipient_id=str(user.pk),
        event_type="deck.card_changed",
        subject_type="deck_card",
        subject_id="deck-1:card-1",
        target_url="/my/decks/deck-1",
        title="Card changed in deck",
        message="First update",
        metadata={"version": 1},
        dedupe_key="deck.card_changed:unread-conflict",
    )
    first = create_or_coalesce_notification(data)
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)
    read_response = client.patch(
        f"/notifications/{first.id}",
        data={"read": True},
        content_type="application/json",
    )
    assert read_response.status_code == 200
    second = create_or_coalesce_notification(
        NotificationInput(
            **{
                **data.__dict__,
                "message": "Second update",
                "metadata": {"version": 2},
            }
        )
    )
    assert second.id != first.id

    unread_response = client.patch(
        f"/notifications/{first.id}",
        data={"read": False},
        content_type="application/json",
    )

    assert unread_response.status_code == 409
    assert unread_response.json()["active_notification"]["id"] == second.id
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.read_at is not None
    assert second.read_at is None


@override_settings(CARD_READER_AUTH_ENABLED=False)
def test_notifications_are_empty_when_auth_is_disabled() -> None:
    _clear_notifications()
    response = Client(HTTP_HOST="localhost").get("/notifications")
    summary_response = Client(HTTP_HOST="localhost").get("/notifications/summary")
    update_response = Client(HTTP_HOST="localhost").post("/notifications/mark-all-read")

    assert response.status_code == 200
    assert response.json()["results"] == []
    assert summary_response.status_code == 200
    assert summary_response.json()["unread_count"] == 0
    assert update_response.status_code == 403


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_parse_flag_review_creates_submitter_notification() -> None:
    _clear_notifications()
    submitter = _create_user("notification-flag-submit", "password")
    reviewer = _create_user("notification-flag-reviewer", "password", is_staff=True)
    card, version = _create_card_version(name="Notification Flag Card")
    submit_client = Client(HTTP_HOST="localhost")
    submit_client.force_login(submitter)
    submit_response = submit_client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={"items": [{"property_key": "name"}]},
        content_type="application/json",
    )
    assert submit_response.status_code == 201
    review_client = Client(HTTP_HOST="localhost")
    review_client.force_login(reviewer)
    flag = review_client.get("/review/parse-flags").json()["results"][0]
    item_id = flag["items"][0]["id"]

    review_response = review_client.patch(
        f"/review/parse-flags/items/{item_id}",
        data={"status": "resolved"},
        content_type="application/json",
    )

    assert review_response.status_code == 200
    notification = UserNotification.objects.get(recipient_id=str(submitter.pk))
    assert notification.event_type == "parse_flag.reviewed"
    assert notification.actor_id == reviewer.pk
    assert notification.subject_id == item_id
    assert notification.target_url == f"/cards/{card.id}"


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_update_does_not_notify_deck_owner() -> None:
    _clear_notifications()
    owner = _create_user("notification-deck-owner", "password")
    actor = _create_user("notification-card-editor", "password", is_staff=True)
    hero = _create_card(name="Notification Hero", is_hero=True)
    card = _create_card(name="Notification Mainboard", is_hero=False)
    DeckService().create_owner_deck(
        owner_id=str(owner.pk),
        name="Notification Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=1)],
        sideboards=[],
    )

    updated = update_latest_card_version_with_notifications(
        card_id=card.id,
        updates={"rules_text": "Changed rules"},
        restore_fields=[],
        restore_metadata_groups=[],
        unlock_fields=[],
        unlock_metadata_groups=[],
        actor_id=str(actor.pk),
    )

    assert updated is not None
    assert UserNotification.objects.filter(recipient_id=str(owner.pk)).count() == 0
    assert UserNotification.objects.filter(recipient_id=str(actor.pk)).count() == 0


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_card_promotion_notifies_sideboard_deck_owner() -> None:
    _clear_notifications()
    owner = _create_user("notification-sideboard-owner", "password")
    actor = _create_user("notification-sideboard-editor", "password", is_staff=True)
    hero = _create_card(name="Notification Sideboard Hero", is_hero=True)
    card = _create_card(name="Notification Sideboard Card", is_hero=False)
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.pk),
        name="Notification Sideboard Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[],
        sideboards=[DeckSideboardInput(name="Maybe", entries=[DeckEntryInput(card_id=card.id, quantity=1)])],
    )
    current_version = card.latest_version
    assert current_version is not None
    promoted_version = CardVersion.objects.create(
        card=card,
        version_number=2,
        template=current_version.template,
        image_hash=f"promotion-hash-{card.id}",
        name=card.label,
        type_line=current_version.type_line,
        mana_cost=current_version.mana_cost,
        mana_symbols_json=current_version.mana_symbols_json,
        rules_text_raw=current_version.rules_text_raw,
        rules_text_enriched=current_version.rules_text_enriched,
        rules_text=current_version.rules_text,
        confidence=current_version.confidence,
        field_sources_json=current_version.field_sources_json,
        parsed_snapshot_json=current_version.parsed_snapshot_json,
        is_latest=False,
    )
    ParseResult.objects.create(
        card_version=promoted_version,
        raw_ocr_json={},
        normalized_fields_json={},
        confidence_json={},
    )

    promoted = promote_card_version_with_notifications(
        card_id=card.id,
        version_id=promoted_version.id,
        actor_id=str(actor.pk),
    )

    assert promoted is not None
    notification = UserNotification.objects.get(recipient_id=str(owner.pk))
    assert notification.subject_id == f"{deck.id}:{card.id}"
    assert notification.metadata_json["change_label"] == "promoted"


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_noop_card_promotion_does_not_notify_deck_owner() -> None:
    _clear_notifications()
    owner = _create_user("notification-noop-promotion-owner", "password")
    actor = _create_user("notification-noop-promotion-editor", "password", is_staff=True)
    hero = _create_card(name="Notification Noop Promotion Hero", is_hero=True)
    card = _create_card(name="Notification Noop Promotion Card", is_hero=False)
    DeckService().create_owner_deck(
        owner_id=str(owner.pk),
        name="Notification Noop Promotion Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=1)],
        sideboards=[],
    )
    current_version = card.latest_version
    assert current_version is not None

    promoted = promote_card_version_with_notifications(
        card_id=card.id,
        version_id=current_version.id,
        actor_id=str(actor.pk),
    )

    assert promoted is not None
    assert UserNotification.objects.filter(recipient_id=str(owner.pk)).count() == 0
    assert UserNotification.objects.filter(recipient_id=str(actor.pk)).count() == 0


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_import_reparse_does_not_notify_affected_deck_owner() -> None:
    _clear_notifications()
    owner = _create_user("notification-import-owner", "password")
    hero = _create_card(name="Notification Import Hero", is_hero=True)
    card = _create_card(name="Notification Import Card", is_hero=False)
    DeckService().create_owner_deck(
        owner_id=str(owner.pk),
        name="Notification Import Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=1)],
        sideboards=[],
    )
    current_version = card.latest_version
    assert current_version is not None
    job = ImportJob.objects.create(
        source_path="uploads/import-replacement.png",
        template=Template.objects.get(key="deck-test-template"),
        total_items=1,
    )
    item = ImportJobItem.objects.create(
        job=job,
        source_file="uploads/import-replacement.png",
        target_card=card,
        target_card_version=current_version,
    )

    save_parsed_card_with_notifications(
        item=item,
        template_id="deck-test-template",
        checksum="import-replacement-checksum",
        normalized_fields={
            "name": card.label,
            "type_line": "Follower",
            "mana_cost": "",
            "rules_text": "Imported rules",
            "rules_text_raw": "Imported rules",
            "rules_text_enriched": "Imported rules",
        },
        confidence={"overall": 0.9},
        raw_ocr={},
        reparse_existing=False,
    )

    assert UserNotification.objects.filter(recipient_id=str(owner.pk)).count() == 0


@override_settings(CARD_READER_AUTH_ENABLED=True)
def test_import_new_version_notifies_affected_deck_owner() -> None:
    _clear_notifications()
    owner = _create_user("notification-import-new-owner", "password")
    hero = _create_card(name="Notification Import New Hero", is_hero=True)
    card = _create_card(name="Notification Import New Card", is_hero=False)
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.pk),
        name="Notification Import New Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=1)],
        sideboards=[],
    )
    current_version = card.latest_version
    assert current_version is not None
    job = ImportJob.objects.create(
        source_path="uploads/import-new-version.png",
        template=Template.objects.get(key="deck-test-template"),
        total_items=1,
    )
    item = ImportJobItem.objects.create(
        job=job,
        source_file="uploads/import-new-version.png",
    )
    source_file = resolve_storage_path(item.source_file)
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
        b"\x00\x05\xfe\x02\xfeA\xe2&\xb5\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    version = save_parsed_card_with_notifications(
        item=item,
        template_id="deck-test-template",
        checksum="import-new-version-checksum",
        normalized_fields={
            "name": card.label,
            "type_line": "Follower",
            "mana_cost": "",
            "rules_text": "Imported rules",
            "rules_text_raw": "Imported rules",
            "rules_text_enriched": "Imported rules",
        },
        confidence={"overall": 0.9},
        raw_ocr={},
        reparse_existing=False,
    )

    assert version.id != current_version.id
    notification = UserNotification.objects.get(recipient_id=str(owner.pk))
    assert notification.subject_id == f"{deck.id}:{card.id}"
    assert notification.message == f"{card.label} was replaced by an import and appears in your deck."
    assert notification.metadata_json["change_label"] == "replaced by an import"
    assert notification.metadata_json["source"] == "import"
    assert notification.metadata_json["import_job_id"] == job.id
    assert notification.metadata_json["import_item_id"] == item.id


def _create_user(username: str, password: str, *, is_staff: bool = False):
    user_model = get_user_model()
    user_model.objects.filter(username=username).delete()
    user = user_model.objects.create_user(username=username, password=password)
    user.is_staff = is_staff
    user.save(update_fields=["is_staff"])
    return user


def _clear_notifications() -> None:
    UserNotification.objects.all().delete()
