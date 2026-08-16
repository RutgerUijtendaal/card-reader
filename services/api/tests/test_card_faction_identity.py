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
def test_reimport_reuses_unique_image_after_manual_faction_correction() -> None:
    template = Template.objects.create(key="corrected-faction-import", label="Corrected Faction")

    def import_card(source_name: str) -> tuple[CardVersion, ImportJobItem]:
        source_path = build_storage_relative_path("uploads", "faction-correction", source_name)
        path = settings.storage_root_dir / source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"corrected-faction-art")
        job = ImportJob.objects.create(
            source_path="uploads/faction-correction",
            template=template,
            card_pool="evil",
            total_items=1,
        )
        item = ImportJobItem.objects.create(job=job, source_file=source_path)
        version = save_parsed_card(
            item=item,
            template_id=template.key,
            checksum="corrected-faction-art",
            normalized_fields={"name": "Corrected Faction Card"},
            confidence={"overall": 1.0},
            raw_ocr={},
            card_pool="evil",
            resolved_card_factions=(),
        )
        item.refresh_from_db()
        return version, item

    original_version, original_item = import_card("first.webp")
    change_card_identity(card=original_version.card, card_factions=("order",))
    repeated_version, repeated_item = import_card("second.webp")

    original_version.card.refresh_from_db()
    assert original_item.resolved_card_factions_json == []
    assert card_faction_keys(original_version.card) == ("order",)
    assert repeated_version.card_id == original_version.card_id
    assert repeated_item.target_card_id == original_version.card_id
    assert repeated_item.warning_code == "card_classification_mismatch"
    assert repeated_item.resolved_card_factions_json == []


@pytest.mark.django_db
def test_reimport_does_not_reuse_correction_provenance_from_another_pool() -> None:
    template = Template.objects.create(key="moved-pool-import", label="Moved Pool")
    source_path = build_storage_relative_path("uploads", "moved-pool", "player.webp")
    path = settings.storage_root_dir / source_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"moved-pool-art")
    player_job = ImportJob.objects.create(
        source_path="uploads/moved-pool",
        template=template,
        card_pool="player",
        total_items=1,
    )
    player_item = ImportJobItem.objects.create(job=player_job, source_file=source_path)
    player_version = save_parsed_card(
        item=player_item,
        template_id=template.key,
        checksum="moved-pool-art",
        normalized_fields={"name": "Moved Pool Card"},
        confidence={"overall": 1.0},
        raw_ocr={},
        card_pool="player",
        resolved_card_factions=(),
    )
    change_card_identity(
        card=player_version.card,
        card_pool="evil",
        card_factions=("order",),
    )

    evil_job = ImportJob.objects.create(
        source_path="uploads/moved-pool",
        template=template,
        card_pool="evil",
        total_items=1,
    )
    evil_item = ImportJobItem.objects.create(job=evil_job, source_file=source_path)
    evil_version = save_parsed_card(
        item=evil_item,
        template_id=template.key,
        checksum="moved-pool-art",
        normalized_fields={"name": "Moved Pool Card"},
        confidence={"overall": 1.0},
        raw_ocr={},
        card_pool="evil",
        resolved_card_factions=(),
    )

    assert evil_version.card_id != player_version.card_id
    assert card_faction_keys(evil_version.card) == ()


@pytest.mark.django_db
def test_reimport_reuses_corrected_card_when_provenance_version_is_not_latest() -> None:
    template = Template.objects.create(key="historical-faction-import", label="Historical Faction")
    source_path = build_storage_relative_path("uploads", "historical-faction", "original.webp")
    path = settings.storage_root_dir / source_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"historical-faction-art")
    original_job = ImportJob.objects.create(
        source_path="uploads/historical-faction",
        template=template,
        card_pool="evil",
        total_items=1,
    )
    original_item = ImportJobItem.objects.create(job=original_job, source_file=source_path)
    original_version = save_parsed_card(
        item=original_item,
        template_id=template.key,
        checksum="historical-faction-art",
        normalized_fields={"name": "Historical Faction Card"},
        confidence={"overall": 1.0},
        raw_ocr={},
        card_pool="evil",
        resolved_card_factions=(),
    )
    change_card_identity(card=original_version.card, card_factions=("dark",))
    original_version.is_latest = False
    original_version.save(update_fields=["is_latest"])
    newer_version = CardVersion.objects.create(
        card=original_version.card,
        template=template,
        version_number=2,
        image_hash="newer-faction-art",
        name=original_version.name,
        previous_version=original_version,
    )
    original_version.card.latest_version = newer_version
    original_version.card.save(update_fields=["latest_version"])

    repeated_job = ImportJob.objects.create(
        source_path="uploads/historical-faction",
        template=template,
        card_pool="evil",
        total_items=1,
    )
    repeated_item = ImportJobItem.objects.create(job=repeated_job, source_file=source_path)
    repeated_version = save_parsed_card(
        item=repeated_item,
        template_id=template.key,
        checksum="historical-faction-art",
        normalized_fields={"name": "Historical Faction Card"},
        confidence={"overall": 1.0},
        raw_ocr={},
        card_pool="evil",
        resolved_card_factions=(),
    )

    repeated_item.refresh_from_db()
    assert repeated_version.card_id == original_version.card_id
    assert repeated_version.id not in {original_version.id, newer_version.id}
    assert repeated_version.version_number == 3
    assert repeated_version.previous_version_id == newer_version.id
    assert repeated_item.warning_code == "card_classification_mismatch"
    assert card_faction_keys(repeated_version.card) == ("dark",)


@pytest.mark.django_db
def test_reimport_does_not_treat_targeted_classification_mismatch_as_correction() -> None:
    template = Template.objects.create(key="targeted-mismatch-import", label="Targeted Mismatch")
    corrected_card, _created = create_card_identity(
        name="Targeted Mismatch Card",
        card_pool="evil",
        card_factions=("order",),
    )
    target_version = CardVersion.objects.create(
        card=corrected_card,
        template=template,
        image_hash="targeted-mismatch-art",
        name=corrected_card.label,
    )
    corrected_card.latest_version = target_version
    corrected_card.save(update_fields=["latest_version"])
    source_path = build_storage_relative_path("uploads", "targeted-mismatch", "source.webp")
    path = settings.storage_root_dir / source_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"targeted-mismatch-art")
    reparse_job = ImportJob.objects.create(
        source_path="uploads/targeted-mismatch",
        template=template,
        card_pool="evil",
        total_items=1,
    )
    reparse_item = ImportJobItem.objects.create(
        job=reparse_job,
        source_file=source_path,
        target_card=corrected_card,
        target_card_version=target_version,
        target_card_pool_snapshot="evil",
        target_card_factions_snapshot_json=["order"],
    )
    save_parsed_card(
        item=reparse_item,
        template_id=template.key,
        checksum="targeted-mismatch-art",
        normalized_fields={"name": "Targeted Mismatch Card"},
        confidence={"overall": 1.0},
        raw_ocr={},
        card_pool="evil",
        resolved_card_factions=(),
    )
    reparse_item.refresh_from_db()
    assert reparse_item.warning_code == "card_classification_mismatch"

    untargeted_job = ImportJob.objects.create(
        source_path="uploads/targeted-mismatch",
        template=template,
        card_pool="evil",
        total_items=1,
    )
    untargeted_item = ImportJobItem.objects.create(
        job=untargeted_job,
        source_file=source_path,
    )
    untargeted_version = save_parsed_card(
        item=untargeted_item,
        template_id=template.key,
        checksum="targeted-mismatch-art",
        normalized_fields={"name": "Independent Mismatch Card"},
        confidence={"overall": 1.0},
        raw_ocr={},
        card_pool="evil",
        resolved_card_factions=(),
    )

    assert untargeted_version.card_id != corrected_card.id
    assert card_faction_keys(untargeted_version.card) == ()


@pytest.mark.django_db
def test_reimport_does_not_treat_role_mismatch_as_faction_correction() -> None:
    template = Template.objects.create(key="role-mismatch-import", label="Role Mismatch")
    source_path = build_storage_relative_path("uploads", "role-mismatch", "source.webp")
    path = settings.storage_root_dir / source_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"role-mismatch-art")

    def import_card(*, name: str, roles: tuple[CardRole, ...]) -> tuple[CardVersion, ImportJobItem]:
        job = ImportJob.objects.create(
            source_path="uploads/role-mismatch",
            template=template,
            card_pool="evil",
            total_items=1,
        )
        item = ImportJobItem.objects.create(job=job, source_file=source_path)
        version = save_parsed_card(
            item=item,
            template_id=template.key,
            checksum="role-mismatch-art",
            normalized_fields={"name": name},
            confidence={"overall": 1.0},
            raw_ocr={},
            card_pool="evil",
            resolved_card_roles=roles,
            resolved_card_factions=(),
        )
        item.refresh_from_db()
        return version, item

    original_version, _original_item = import_card(
        name="Role Mismatch Card",
        roles=("boss",),
    )
    mismatch_version, mismatch_item = import_card(
        name="Role Mismatch Card",
        roles=(),
    )
    assert mismatch_version.card_id == original_version.card_id
    assert mismatch_item.warning_code == "card_classification_mismatch"

    change_card_identity(card=original_version.card, card_factions=("order",))
    independent_version, _independent_item = import_card(
        name="Independent Role Mismatch Card",
        roles=(),
    )

    assert independent_version.card_id != original_version.card_id
    assert card_faction_keys(independent_version.card) == ()


@pytest.mark.django_db
def test_reimport_does_not_cross_faction_namespace_when_corrected_image_is_ambiguous() -> None:
    template = Template.objects.create(key="ambiguous-faction-import", label="Ambiguous Faction")
    corrected_cards = []
    for index, faction in enumerate(("order", "blood")):
        card, _created = create_card_identity(
            name=f"Corrected Twin {index}",
            card_pool="evil",
            card_factions=(faction,),
        )
        version = CardVersion.objects.create(
            card=card,
            template=template,
            image_hash="ambiguous-corrected-art",
            name=card.label,
        )
        card.latest_version = version
        card.save(update_fields=["latest_version"])
        prior_job = ImportJob.objects.create(
            source_path=f"uploads/ambiguous-correction-{index}",
            template=template,
            card_pool="evil",
            total_items=1,
        )
        ImportJobItem.objects.create(
            job=prior_job,
            source_file=f"uploads/ambiguous-correction-{index}.webp",
            target_card=card,
            target_card_version=version,
            status="completed",
            resolved_card_roles_json=[],
            resolved_card_factions_json=[],
            classification_inference_json={
                "live_classification": {
                    "card_pool": "evil",
                    "card_roles": [],
                    "card_factions": [],
                }
            },
        )
        corrected_cards.append(card)

    source_path = build_storage_relative_path("uploads", "ambiguous-correction-new.webp")
    path = settings.storage_root_dir / source_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"ambiguous-corrected-art")
    job = ImportJob.objects.create(
        source_path="uploads/ambiguous-correction-new.webp",
        template=template,
        card_pool="evil",
        total_items=1,
    )
    item = ImportJobItem.objects.create(job=job, source_file=source_path)

    version = save_parsed_card(
        item=item,
        template_id=template.key,
        checksum="ambiguous-corrected-art",
        normalized_fields={"name": "Ambiguous New Card"},
        confidence={"overall": 1.0},
        raw_ocr={},
        card_pool="evil",
        resolved_card_factions=(),
    )

    assert version.card_id not in {card.id for card in corrected_cards}
    assert card_faction_keys(version.card) == ()


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
