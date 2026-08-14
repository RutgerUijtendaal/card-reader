from __future__ import annotations

from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client
import pytest

from card_reader_core.config import settings
from card_reader_core.models import (
    CardMergeRedirect,
    CardVersion,
    ImportJob,
    ImportJobItem,
    ParseResult,
    Template,
    UserNotification,
    now_utc,
)
from card_reader_core.services.cards import (
    promote_card_version_with_notifications,
    save_parsed_card_with_notifications,
    update_latest_card_version_with_notifications,
)
from card_reader_core.repositories.notifications import NotificationInput, create_or_coalesce_notification
from card_reader_core.services.decks import DeckEntryInput, DeckService, DeckSideboardInput
from card_reader_core.services.notifications import (
    DECK_CARD_VERSION_CHANGE_VERSION_PROMOTED,
    NotificationService,
)
from card_reader_core.services.tts_card_sheets import TtsCardSheetService
from card_reader_core.storage import resolve_storage_path
from test_decks import _create_card
from test_parse_flags import _create_card_version


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


def test_notifications_coalesce_and_mark_all_read() -> None:
    _clear_notifications()
    user = _create_user("notification-coalesce", "password")
    data = NotificationInput(
        recipient_id=str(user.pk),
        event_type="deck.card_version_changed",
        subject_type="deck_card",
        subject_id="deck-1:card-1",
        target_url="/my/decks/deck-1",
        title="Card changed in deck",
        message="First update",
        metadata={"version": 1},
        dedupe_key="deck.card_version_changed:deck-1:card-1",
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


def test_notification_api_filters_by_known_event_type() -> None:
    _clear_notifications()
    user = _create_user("notification-event-filter", "password")
    for event_type in ["parse_flag_item.reviewed", "deck.card_version_changed"]:
        create_or_coalesce_notification(
            NotificationInput(
                recipient_id=str(user.pk),
                event_type=event_type,
                subject_type="test",
                subject_id=event_type,
                target_url="/notifications",
                title=event_type,
                message="Filtered notification",
                metadata={},
            )
        )
    client = Client(HTTP_HOST="localhost")
    client.force_login(user)

    filtered_response = client.get(
        "/notifications?event_type=parse_flag_item.reviewed&page=1&page_size=25"
    )
    invalid_response = client.get("/notifications?event_type=unknown.event")

    assert filtered_response.status_code == 200
    assert filtered_response.json()["count"] == 1
    assert filtered_response.json()["results"][0]["event_type"] == "parse_flag_item.reviewed"
    assert invalid_response.status_code == 400


def test_notification_coalesce_retry_preserves_outer_transaction(monkeypatch) -> None:
    _clear_notifications()
    user = _create_user("notification-race-user", "password")
    data = NotificationInput(
        recipient_id=str(user.pk),
        event_type="deck.card_version_changed",
        subject_type="deck_card",
        subject_id="deck-1:card-1",
        target_url="/my/decks/deck-1",
        title="Card changed in deck",
        message="First update",
        metadata={"version": 1},
        dedupe_key="deck.card_version_changed:race",
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


def test_notification_coalesce_retries_when_found_row_becomes_read(monkeypatch) -> None:
    _clear_notifications()
    user = _create_user("notification-stale-dedupe-user", "password")
    data = NotificationInput(
        recipient_id=str(user.pk),
        event_type="deck.card_version_changed",
        subject_type="deck_card",
        subject_id="deck-1:card-1",
        target_url="/my/decks/deck-1",
        title="Card changed in deck",
        message="First update",
        metadata={"version": 1},
        dedupe_key="deck.card_version_changed:stale-row",
    )
    stale = create_or_coalesce_notification(data)

    from card_reader_core.repositories.notifications import writes

    original_queryset = writes._active_dedupe_queryset
    original_create = writes._create_notification
    state = {"returned_stale": False}
    active_holder: dict[str, UserNotification] = {}

    class StaleDedupeLookup:
        def order_by(self, *_fields: str) -> StaleDedupeLookup:
            return self

        def first(self) -> UserNotification:
            state["returned_stale"] = True
            stale.read_at = now_utc()
            stale.save(update_fields=["read_at"])
            active_holder["notification"] = original_create(
                NotificationInput(
                    **{
                        **data.__dict__,
                        "message": "Concurrent update",
                        "metadata": {"version": 2},
                    }
                )
            )
            return stale

    def race_queryset(input_data: NotificationInput):
        if not state["returned_stale"]:
            return StaleDedupeLookup()
        return original_queryset(input_data)

    monkeypatch.setattr(writes, "_active_dedupe_queryset", race_queryset)

    updated = create_or_coalesce_notification(
        NotificationInput(
            **{
                **data.__dict__,
                "message": "Race update",
                "metadata": {"version": 3},
            }
        )
    )

    active = active_holder["notification"]
    assert updated.id == active.id
    updated.refresh_from_db()
    stale.refresh_from_db()
    assert stale.read_at is not None
    assert updated.event_count == 2
    assert updated.message == "Race update"
    assert UserNotification.objects.filter(recipient_id=str(user.pk), read_at__isnull=True).count() == 1


def test_marking_read_deduped_notification_unread_conflicts_with_active_unread() -> None:
    _clear_notifications()
    user = _create_user("notification-unread-conflict", "password")
    data = NotificationInput(
        recipient_id=str(user.pk),
        event_type="deck.card_version_changed",
        subject_type="deck_card",
        subject_id="deck-1:card-1",
        target_url="/my/decks/deck-1",
        title="Card changed in deck",
        message="First update",
        metadata={"version": 1},
        dedupe_key="deck.card_version_changed:unread-conflict",
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


def test_notifications_are_empty_for_unauthenticated_users() -> None:
    _clear_notifications()
    response = Client(HTTP_HOST="localhost").get("/notifications")
    summary_response = Client(HTTP_HOST="localhost").get("/notifications/summary")
    update_response = Client(HTTP_HOST="localhost").post("/notifications/mark-all-read")

    assert response.status_code == 200
    assert response.json()["results"] == []
    assert summary_response.status_code == 200
    assert summary_response.json()["unread_count"] == 0
    assert update_response.status_code == 403


def test_notification_event_name_migration_preserves_rows_and_dedupe_keys() -> None:
    _clear_notifications()
    user = _create_user("notification-migration", "password")
    flag_notification = create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(user.pk),
            event_type="parse_flag.reviewed",
            subject_type="parse_flag_item",
            subject_id="flag-item-1",
            target_url="/cards/card-1",
            title="Flag reviewed",
            message="Reviewed",
            metadata={},
            dedupe_key="parse_flag.reviewed:flag-item-1",
        )
    )
    original_read_at = now_utc()
    UserNotification.objects.filter(id=flag_notification.id).update(event_count=4, read_at=original_read_at)
    deck_notification = create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(user.pk),
            event_type="deck.card_changed",
            subject_type="deck_card",
            subject_id="deck-1:card-1",
            target_url="/my/decks/deck-1",
            title="Card changed",
            message="Changed",
            metadata={},
            dedupe_key="deck.card_changed:deck-1:card-1",
        )
    )
    migration = import_module("card_reader_core.migrations.0043_notification_event_names")

    migration.rename_notification_event_types(apps, None)

    flag_notification.refresh_from_db()
    deck_notification.refresh_from_db()
    assert flag_notification.event_type == "parse_flag_item.reviewed"
    assert flag_notification.dedupe_key == "parse_flag_item.reviewed:flag-item-1"
    assert flag_notification.event_count == 4
    assert flag_notification.read_at == original_read_at
    assert deck_notification.event_type == "deck.card_version_changed"
    assert deck_notification.dedupe_key == "deck.card_version_changed:deck-1:card-1"

    migration.restore_notification_event_types(apps, None)
    flag_notification.refresh_from_db()
    deck_notification.refresh_from_db()
    assert flag_notification.event_type == "parse_flag.reviewed"
    assert flag_notification.dedupe_key == "parse_flag.reviewed:flag-item-1"
    assert deck_notification.event_type == "deck.card_changed"
    assert deck_notification.dedupe_key == "deck.card_changed:deck-1:card-1"


def test_notification_previous_version_migration_backfills_only_safe_rows() -> None:
    _clear_notifications()
    user = _create_user("notification-version-migration", "password")
    card = _create_card(name="Notification Version Migration Card", hero=False)
    previous_version = card.latest_version
    assert previous_version is not None
    current_version = CardVersion.objects.create(
        card=card,
        version_number=2,
        template=previous_version.template,
        image_hash=f"migration-hash-{card.id}",
        name=card.label,
        previous_version=previous_version,
    )
    notification = create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(user.pk),
            event_type="deck.card_version_changed",
            subject_type="deck_card",
            subject_id=f"deck-1:{card.id}",
            target_url="/my/decks/deck-1",
            title="Card changed",
            message="Changed",
            metadata={
                "card_id": card.id,
                "card_version_id": current_version.id,
            },
        )
    )
    original_read_at = now_utc()
    UserNotification.objects.filter(id=notification.id).update(
        event_count=4,
        read_at=original_read_at,
    )
    existing_value = create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(user.pk),
            event_type="deck.card_version_changed",
            subject_type="deck_card",
            subject_id=f"deck-2:{card.id}",
            target_url="/my/decks/deck-2",
            title="Card changed",
            message="Changed",
            metadata={
                "card_id": card.id,
                "card_version_id": current_version.id,
                "previous_card_version_id": "already-recorded",
            },
        )
    )
    mismatched_card = _create_card(name="Mismatched Notification Card", hero=False)
    mismatched = create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(user.pk),
            event_type="deck.card_version_changed",
            subject_type="deck_card",
            subject_id=f"deck-3:{mismatched_card.id}",
            target_url="/my/decks/deck-3",
            title="Card changed",
            message="Changed",
            metadata={
                "card_id": mismatched_card.id,
                "card_version_id": current_version.id,
            },
        )
    )
    migration = import_module(
        "card_reader_core.migrations.0044_backfill_notification_previous_versions"
    )

    migration.backfill_notification_previous_versions(apps, None)
    migration.backfill_notification_previous_versions(apps, None)

    notification.refresh_from_db()
    existing_value.refresh_from_db()
    mismatched.refresh_from_db()
    assert notification.metadata_json["previous_card_version_id"] == previous_version.id
    assert notification.event_count == 4
    assert notification.read_at == original_read_at
    assert existing_value.metadata_json["previous_card_version_id"] == "already-recorded"
    assert "previous_card_version_id" not in mismatched.metadata_json


def test_parse_flag_review_creates_submitter_notification() -> None:
    _clear_notifications()
    submitter = _create_user("notification-flag-submit", "password")
    reviewer = _create_user("notification-flag-reviewer", "password", is_staff=True)
    card, version = _create_card_version(name="Notification Flag Card")
    submit_client = Client(HTTP_HOST="localhost")
    submit_client.force_login(submitter)
    submit_response = submit_client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={
            "note": "The printed name does not match.",
            "items": [
                {
                    "property_key": "name",
                    "expected_value": "Corrected Notification Flag Card",
                    "note": "The first word is difficult to read.",
                }
            ],
        },
        content_type="application/json",
    )
    assert submit_response.status_code == 201
    review_client = Client(HTTP_HOST="localhost")
    review_client.force_login(reviewer)
    flag = review_client.get("/review/parse-flags").json()["results"][0]
    item_id = flag["items"][0]["id"]

    review_response = review_client.patch(
        f"/review/parse-flags/items/{item_id}",
        data={"status": "resolved", "review_note": "Updated from a clearer source image."},
        content_type="application/json",
    )

    assert review_response.status_code == 200
    notification = UserNotification.objects.get(recipient_id=str(submitter.pk))
    assert notification.event_type == "parse_flag_item.reviewed"
    assert notification.actor_id == reviewer.pk
    assert notification.subject_id == item_id
    assert notification.target_url == f"/cards/{card.id}?version_id={version.id}"
    assert notification.message == "notification-flag-reviewer resolved your name flag."
    assert notification.metadata_json == {
        "card_id": card.id,
        "card_name": version.name,
        "card_version_id": version.id,
        "flag_id": flag["id"],
        "property_key": "name",
        "property_label": "name flag",
        "status": "resolved",
        "submitted_value": "Corrected Notification Flag Card",
        "submission_note": "The first word is difficult to read.",
        "reviewer_name": "notification-flag-reviewer",
        "review_note": "Updated from a clearer source image.",
    }
    payload = submit_client.get("/notifications?status=all").json()["results"][0]
    assert payload["event_type"] == "parse_flag_item.reviewed"
    assert payload["metadata"] == notification.metadata_json


def test_parse_flag_review_notification_is_hidden_after_card_moves_out_of_submitter_scope() -> None:
    _clear_notifications()
    submitter = _create_user("notification-gm-flag-submit", "password")
    reviewer = _create_user("notification-gm-flag-reviewer", "password", is_staff=True)
    card, version = _create_card_version(name="Notification Reclassified Flag Card")
    submit_client = Client(HTTP_HOST="localhost")
    submit_client.force_login(submitter)
    submit_response = submit_client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={
            "items": [
                {
                    "property_key": "name",
                    "expected_value": "Corrected Reclassified Flag Card",
                }
            ],
        },
        content_type="application/json",
    )
    assert submit_response.status_code == 201
    card.card_pool = "evil"
    card.save(update_fields=["card_pool"])
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
    assert UserNotification.objects.filter(recipient_id=str(submitter.pk)).exists()
    assert submit_client.get("/notifications?status=all").json()["count"] == 0


def test_staff_submitter_receives_parse_review_notification_for_evil_card() -> None:
    _clear_notifications()
    submitter = _create_user("notification-evil-flag-submit", "password", is_staff=True)
    reviewer = _create_user("notification-evil-flag-reviewer", "password", is_staff=True)
    card, version = _create_card_version(name="Notification Evil Flag Card")
    card.card_pool = "evil"
    card.save(update_fields=["card_pool"])
    submit_client = Client(HTTP_HOST="localhost")
    submit_client.force_login(submitter)
    submit_response = submit_client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={"items": [{"property_key": "name", "expected_value": "Corrected Evil Card"}]},
        content_type="application/json",
    )
    assert submit_response.status_code == 201
    reviewer_client = Client(HTTP_HOST="localhost")
    reviewer_client.force_login(reviewer)
    flag = reviewer_client.get("/review/parse-flags").json()["results"][0]

    response = reviewer_client.patch(
        f"/review/parse-flags/items/{flag['items'][0]['id']}",
        data={"status": "resolved"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert submit_client.get("/notifications?status=all").json()["count"] == 1


def test_parse_flag_self_review_creates_notification_in_development(monkeypatch) -> None:
    _clear_notifications()
    monkeypatch.setattr(settings, "environment", "development")

    reviewer, review_response = _submit_and_resolve_own_flag(
        username="notification-self-review-dev",
        card_name="Development Self Review Card",
    )

    assert review_response.status_code == 200
    notification = UserNotification.objects.get(recipient_id=str(reviewer.pk))
    assert notification.actor_id == reviewer.pk
    assert notification.event_type == "parse_flag_item.reviewed"


def test_parse_flag_self_review_stays_silent_in_production(monkeypatch) -> None:
    _clear_notifications()
    monkeypatch.setattr(settings, "environment", "production")

    reviewer, review_response = _submit_and_resolve_own_flag(
        username="notification-self-review-production",
        card_name="Production Self Review Card",
    )

    assert review_response.status_code == 200
    assert not UserNotification.objects.filter(recipient_id=str(reviewer.pk)).exists()


def test_card_update_does_not_notify_deck_owner() -> None:
    _clear_notifications()
    owner = _create_user("notification-deck-owner", "password")
    actor = _create_user("notification-card-editor", "password", is_staff=True)
    hero = _create_card(name="Notification Hero", hero=True)
    card = _create_card(name="Notification Mainboard", hero=False)
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


@pytest.mark.django_db(transaction=True)
def test_card_promotion_notifies_sideboard_deck_owner() -> None:
    _clear_notifications()
    owner = _create_user("notification-sideboard-owner", "password")
    actor = _create_user("notification-sideboard-editor", "password", is_staff=True)
    hero = _create_card(name="Notification Sideboard Hero", hero=True)
    card = _create_card(name="Notification Sideboard Card", hero=False)
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
    assert notification.event_type == "deck.card_version_changed"
    assert notification.subject_id == f"{deck.id}:{card.id}"
    assert notification.metadata_json["change_cause"] == "version_promoted"
    assert notification.metadata_json["card_version_id"] == promoted_version.id
    assert notification.metadata_json["previous_card_version_id"] == current_version.id


def test_card_version_change_notifies_hero_deck_owner_but_not_actor() -> None:
    _clear_notifications()
    owner = _create_user("notification-hero-owner", "password")
    actor = _create_user("notification-hero-actor", "password", is_staff=True)
    hero = _create_card(name="Notification Changed Hero", hero=True)
    hero_version = hero.latest_version
    assert hero_version is not None
    deck = DeckService().create_owner_deck(
        owner_id=str(owner.pk),
        name="Notification Hero Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[],
        sideboards=[],
    )
    DeckService().create_owner_deck(
        owner_id=str(actor.pk),
        name="Notification Actor Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[],
        sideboards=[],
    )

    NotificationService().notify_deck_owners_card_version_changed(
        card_id=hero.id,
        card_version_id=hero_version.id,
        previous_card_version_id=None,
        cause=DECK_CARD_VERSION_CHANGE_VERSION_PROMOTED,
        actor_id=str(actor.pk),
    )
    NotificationService().notify_deck_owners_card_version_changed(
        card_id=hero.id,
        card_version_id=hero_version.id,
        previous_card_version_id=None,
        cause=DECK_CARD_VERSION_CHANGE_VERSION_PROMOTED,
        actor_id=str(actor.pk),
    )

    notification = UserNotification.objects.get(recipient_id=str(owner.pk))
    assert notification.subject_id == f"{deck.id}:{hero.id}"
    assert notification.event_count == 2
    assert not UserNotification.objects.filter(recipient_id=str(actor.pk)).exists()


@pytest.mark.django_db(transaction=True)
def test_evil_reclassification_hides_card_notifications_and_stops_future_deck_delivery() -> None:
    _clear_notifications()
    owner = _create_user("notification-reclassified-owner", "password")
    hero = _create_card(name="Notification Reclassified Hero", hero=True)
    card = _create_card(name="Notification Reclassified Card", hero=False)
    DeckService().create_owner_deck(
        owner_id=str(owner.pk),
        name="Notification Reclassified Deck",
        description=None,
        visibility="private",
        hero_card_id=hero.id,
        entries=[DeckEntryInput(card_id=card.id, quantity=1)],
        sideboards=[],
    )
    version = card.latest_version
    assert version is not None
    service = NotificationService()
    created = service.notify_deck_owners_card_version_changed(
        card_id=card.id,
        card_version_id=version.id,
        previous_card_version_id=None,
        cause=DECK_CARD_VERSION_CHANGE_VERSION_PROMOTED,
    )
    create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(owner.pk),
            event_type="parse_flag_item.reviewed",
            subject_type="parse_flag_item",
            subject_id="reclassified-flag-item",
            target_url=f"/cards/{card.id}?version_id={version.id}",
            title=f"Flag resolved: {card.label}",
            message="A card-linked flag was resolved.",
            metadata={"card_id": card.id, "card_version_id": version.id},
        )
    )
    merged_source_card_id = "notification-reclassified-merged-source"
    CardMergeRedirect.objects.create(old_card_id=merged_source_card_id, target_card=card)
    create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(owner.pk),
            event_type="parse_flag_item.reviewed",
            subject_type="parse_flag_item",
            subject_id="reclassified-merged-source-flag-item",
            target_url=f"/cards/{merged_source_card_id}",
            title="Flag resolved: merged source",
            message="A merged-source card-linked flag was resolved.",
            metadata={"card_id": merged_source_card_id, "card_version_id": version.id},
        )
    )
    assert len(created) == 1
    assert UserNotification.objects.filter(recipient_id=str(owner.pk), archived_at__isnull=True).count() == 3

    updated = update_latest_card_version_with_notifications(
        card_id=card.id,
        updates={"card_pool": "evil"},
        restore_fields=[],
        restore_metadata_groups=[],
        unlock_fields=[],
        unlock_metadata_groups=[],
    )

    assert updated is not None
    assert UserNotification.objects.filter(recipient_id=str(owner.pk), archived_at__isnull=True).count() == 3
    client = Client(HTTP_HOST="localhost")
    client.force_login(owner)
    assert client.get("/notifications?status=all").json()["count"] == 0
    assert service.notify_deck_owners_card_version_changed(
        card_id=card.id,
        card_version_id=version.id,
        previous_card_version_id=None,
        cause=DECK_CARD_VERSION_CHANGE_VERSION_PROMOTED,
    ) == []
    assert UserNotification.objects.filter(recipient_id=str(owner.pk), archived_at__isnull=True).count() == 3


@pytest.mark.django_db(transaction=True)
def test_evil_reclassification_keeps_notifications_stored_while_reconciling_tts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_notifications()
    owner = _create_user("notification-cleanup-failure-owner", "password")
    card = _create_card(name="Notification Cleanup Failure Card", hero=False)
    version = card.latest_version
    assert version is not None
    notification = create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(owner.pk),
            event_type="parse_flag_item.reviewed",
            subject_type="parse_flag_item",
            subject_id="cleanup-failure-flag-item",
            target_url=f"/cards/{card.id}?version_id={version.id}",
            title=f"Flag resolved: {card.label}",
            message="A card-linked flag was resolved.",
            metadata={"card_id": card.id, "card_version_id": version.id},
        )
    )
    merged_source_card_id = "notification-cleanup-failure-merged-source"
    CardMergeRedirect.objects.create(old_card_id=merged_source_card_id, target_card=card)
    redirected_notification = create_or_coalesce_notification(
        NotificationInput(
            recipient_id=str(owner.pk),
            event_type="parse_flag_item.reviewed",
            subject_type="parse_flag_item",
            subject_id="cleanup-failure-merged-source-flag-item",
            target_url=f"/cards/{merged_source_card_id}",
            title="Flag resolved: merged source",
            message="A merged-source card-linked flag was resolved.",
            metadata={"card_id": merged_source_card_id, "card_version_id": version.id},
        )
    )
    synced_card_ids: list[str] = []

    def record_sync(_service: TtsCardSheetService, card_ids: list[str]) -> set[str]:
        synced_card_ids.extend(card_ids)
        return set()

    monkeypatch.setattr(TtsCardSheetService, "sync_cards", record_sync)

    updated = update_latest_card_version_with_notifications(
        card_id=card.id,
        updates={"card_pool": "evil"},
        restore_fields=[],
        restore_metadata_groups=[],
        unlock_fields=[],
        unlock_metadata_groups=[],
    )

    assert updated is not None
    card.refresh_from_db()
    notification.refresh_from_db()
    redirected_notification.refresh_from_db()
    assert card.card_pool == "evil"
    assert notification.archived_at is None
    assert redirected_notification.archived_at is None
    assert synced_card_ids == [card.id]
    client = Client(HTTP_HOST="localhost")
    client.force_login(owner)
    assert client.get("/notifications?status=all").json()["count"] == 0
    assert client.get("/notifications/summary").json()["unread_count"] == 0


def test_noop_card_promotion_does_not_notify_deck_owner() -> None:
    _clear_notifications()
    owner = _create_user("notification-noop-promotion-owner", "password")
    actor = _create_user("notification-noop-promotion-editor", "password", is_staff=True)
    hero = _create_card(name="Notification Noop Promotion Hero", hero=True)
    card = _create_card(name="Notification Noop Promotion Card", hero=False)
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


def test_import_reparse_does_not_notify_affected_deck_owner() -> None:
    _clear_notifications()
    owner = _create_user("notification-import-owner", "password")
    hero = _create_card(name="Notification Import Hero", hero=True)
    card = _create_card(name="Notification Import Card", hero=False)
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


@pytest.mark.django_db(transaction=True)
def test_import_new_version_notifies_affected_deck_owner() -> None:
    _clear_notifications()
    owner = _create_user("notification-import-new-owner", "password")
    hero = _create_card(name="Notification Import New Hero", hero=True)
    card = _create_card(name="Notification Import New Card", hero=False)
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
    assert notification.event_type == "deck.card_version_changed"
    assert notification.subject_id == f"{deck.id}:{card.id}"
    assert notification.message == (
        f"A newly imported version of {card.label} is now current and appears in your deck."
    )
    assert notification.metadata_json["change_cause"] == "import_created"
    assert notification.metadata_json["card_version_id"] == version.id
    assert notification.metadata_json["previous_card_version_id"] == current_version.id
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


def _submit_and_resolve_own_flag(*, username: str, card_name: str):
    reviewer = _create_user(username, "password", is_staff=True)
    card, version = _create_card_version(name=card_name)
    client = Client(HTTP_HOST="localhost")
    client.force_login(reviewer)
    submit_response = client.post(
        f"/cards/{card.id}/versions/{version.id}/flags",
        data={
            "items": [
                {
                    "property_key": "name",
                    "expected_value": f"Corrected {card_name}",
                }
            ]
        },
        content_type="application/json",
    )
    assert submit_response.status_code == 201
    flag_id = submit_response.json()["id"]
    reports = client.get("/review/parse-flags").json()["results"]
    report = next(row for row in reports if row["id"] == flag_id)
    item_id = report["items"][0]["id"]
    review_response = client.patch(
        f"/review/parse-flags/items/{item_id}",
        data={"status": "resolved", "review_note": "Self-review test."},
        content_type="application/json",
    )
    return reviewer, review_response
