from __future__ import annotations

import pytest
import card_reader_core.repositories.cards.edits as card_edits_repository

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    CardAlias,
    CardFaction,
    CardRole,
    CardVersion,
    ImportJob,
    ImportJobItem,
    Template,
    card_faction_keys,
)
from card_reader_core.repositories.cards import (
    CardIdentityConflict,
    change_card_identity,
    create_card_identity,
    ensure_card_alias,
    resolve_card_by_name_key,
    save_parsed_card,
    update_latest_card_version,
)
from card_reader_core.storage import build_storage_relative_path
from card_reader_core.services.card_merges import preview_card_merge


@pytest.mark.django_db
def test_card_identity_is_scoped_by_pool_and_exact_faction_set() -> None:
    order_card, order_created = create_card_identity(
        name="Shared Name",
        card_pool="evil",
        card_factions=("order",),
    )
    blood_card, blood_created = create_card_identity(
        name="Shared Name",
        card_pool="evil",
        card_factions=("blood",),
    )
    multi_card, multi_created = create_card_identity(
        name="Shared Name",
        card_pool="evil",
        card_factions=("dark", "order"),
    )
    repeated_order, repeated_created = create_card_identity(
        name="Shared Name",
        card_pool="evil",
        card_factions=("order",),
    )

    assert order_created and blood_created and multi_created
    assert not repeated_created
    assert repeated_order.id == order_card.id
    assert len({order_card.id, blood_card.id, multi_card.id}) == 3
    assert resolve_card_by_name_key(
        name="Shared Name",
        card_pool="evil",
        card_factions=("order", "dark"),
    ) == multi_card

    ensure_card_alias(card=order_card, key="shared-alias", label="Shared Alias")
    ensure_card_alias(card=blood_card, key="shared-alias", label="Shared Alias")
    assert CardAlias.objects.filter(key="shared-alias").count() == 2


@pytest.mark.django_db
def test_name_pool_and_faction_move_is_atomic_and_moves_every_alias() -> None:
    moving, _ = create_card_identity(
        name="Moving Card",
        card_pool="evil",
        card_factions=("order",),
    )
    ensure_card_alias(card=moving, key="old-alias", label="Old Alias")
    blocker, _ = create_card_identity(
        name="Blocked Name",
        card_pool="neutral",
        card_factions=("blood",),
    )

    with pytest.raises(CardIdentityConflict):
        change_card_identity(
            card=moving,
            label=blocker.label,
            card_pool="neutral",
            card_factions=("blood",),
        )

    moving.refresh_from_db()
    assert moving.label == "Moving Card"
    assert moving.card_pool == "evil"
    assert card_faction_keys(moving) == ("order",)
    assert set(
        CardAlias.objects.filter(card=moving).values_list(
            "card_pool",
            "faction_identity_key",
            "key",
        )
    ) == {("evil", '["order"]', "old-alias")}

    change_card_identity(
        card=moving,
        label="Moved Card",
        card_pool="neutral",
        card_factions=("dark", "order"),
    )
    moving.refresh_from_db()
    assert moving.card_pool == "neutral"
    assert card_faction_keys(moving) == ("order", "dark")
    assert set(
        CardAlias.objects.filter(card=moving).values_list(
            "card_pool",
            "faction_identity_key",
            "key",
        )
    ) == {
        ("neutral", '["order","dark"]', "old-alias"),
        ("neutral", '["order","dark"]', "moving-card"),
    }


@pytest.mark.django_db
def test_pool_only_edit_preserves_a_concurrent_faction_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = Template.objects.create(key="concurrent-classification", label="Concurrent")
    card, _created = create_card_identity(
        name="Concurrent Classification",
        card_pool="player",
        card_factions=(),
    )
    version = CardVersion.objects.create(
        card=card,
        template=template,
        image_hash="concurrent-classification",
        name=card.label,
    )
    card.latest_version = version
    card.save(update_fields=["latest_version"])
    original_change_card_identity = card_edits_repository.change_card_identity
    simulated_overlap = False

    def change_after_stale_read(**kwargs: object):
        nonlocal simulated_overlap
        if not simulated_overlap:
            simulated_overlap = True
            original_change_card_identity(card=card, card_factions=("blood",))
        return original_change_card_identity(**kwargs)

    monkeypatch.setattr(
        card_edits_repository,
        "change_card_identity",
        change_after_stale_read,
    )

    updated = update_latest_card_version(
        card_id=card.id,
        updates={"card_pool": "evil"},
        restore_fields=[],
        restore_metadata_groups=[],
        unlock_fields=[],
        unlock_metadata_groups=[],
    )

    assert updated is not None
    card.refresh_from_db()
    assert card.card_pool == "evil"
    assert card_faction_keys(card) == ("blood",)


@pytest.mark.django_db
def test_untargeted_import_name_and_image_matching_stays_in_exact_faction_namespace() -> None:
    template = Template.objects.create(key="faction-import", label="Faction Import")
    source_paths: list[str] = []
    for name in ("order.webp", "blood.webp", "order-repeat.webp"):
        relative_path = build_storage_relative_path("uploads", "faction-identity", name)
        path = settings.storage_root_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"shared-art")
        source_paths.append(relative_path)

    def save(
        index: int,
        faction: CardFaction,
        role: CardRole,
    ) -> tuple[CardVersion, ImportJobItem]:
        job = ImportJob.objects.create(
            source_path="uploads/faction-identity",
            template=template,
            card_pool="evil",
            total_items=1,
        )
        item = ImportJobItem.objects.create(job=job, source_file=source_paths[index])
        version = save_parsed_card(
            item=item,
            template_id=template.key,
            checksum="shared-faction-art",
            normalized_fields={"name": "Faction Twin"},
            confidence={"overall": 1.0},
            raw_ocr={},
            card_pool="evil",
            resolved_card_roles=(role,),
            resolved_card_factions=(faction,),
        )
        item.refresh_from_db()
        return version, item

    order_version, order_item = save(0, "order", "boss")
    blood_version, blood_item = save(1, "blood", "location")
    repeated_order_version, repeated_order_item = save(2, "order", "boss")

    assert order_version.card_id != blood_version.card_id
    assert repeated_order_version.card_id == order_version.card_id
    assert order_item.warnings_json == []
    assert blood_item.warnings_json == []
    assert repeated_order_item.warnings_json == []


@pytest.mark.django_db
def test_merge_preview_rejects_different_exact_faction_namespaces() -> None:
    order_card, _ = create_card_identity(
        name="Merge Twin",
        card_pool="evil",
        card_factions=("order",),
    )
    blood_card, _ = create_card_identity(
        name="Merge Twin",
        card_pool="evil",
        card_factions=("blood",),
    )

    preview = preview_card_merge(
        target_card_id=order_card.id,
        source_card_ids=[blood_card.id],
    )

    assert preview.blocking_conflicts == [
        "Cards from different faction namespaces cannot be merged."
    ]
    assert preview.target.card_factions == ("order",)
    assert preview.sources[0].card_factions == ("blood",)
