from __future__ import annotations

import pytest
import card_reader_core.repositories.cards.edits as card_edits_repository

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    CardAlias,
    CardClassificationInferenceEvidence,
    CardFaction,
    CardPool,
    CardRole,
    CardVersion,
    ImportJob,
    ImportJobItem,
    Template,
    card_faction_keys,
    card_role_keys,
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


def _import_card(
    *,
    template: Template,
    source_name: str,
    checksum: str,
    name: str,
    card_pool: CardPool = "evil",
    roles: tuple[CardRole, ...] = (),
    factions: tuple[CardFaction, ...] = (),
    reparse_existing: bool = True,
    classification_evidence: CardClassificationInferenceEvidence | None = None,
) -> tuple[CardVersion, ImportJobItem]:
    source_path = build_storage_relative_path("uploads", "faction-identity", source_name)
    path = settings.storage_root_dir / source_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(checksum.encode())
    job = ImportJob.objects.create(
        source_path="uploads/faction-identity",
        template=template,
        card_pool=card_pool,
        total_items=1,
    )
    item = ImportJobItem.objects.create(job=job, source_file=source_path)
    version = save_parsed_card(
        item=item,
        template_id=template.key,
        checksum=checksum,
        normalized_fields={"name": name},
        confidence={"overall": 1.0},
        raw_ocr={},
        reparse_existing=reparse_existing,
        card_pool=card_pool,
        resolved_card_roles=roles,
        resolved_card_factions=factions,
        classification_evidence=classification_evidence,
    )
    item.refresh_from_db()
    return version, item


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
    original_version, original_item = _import_card(
        template=template,
        source_name="corrected-first.webp",
        checksum="corrected-faction-art",
        name="Corrected Faction Card",
        roles=("boss",),
    )
    change_card_identity(card=original_version.card, card_factions=("order",))
    repeated_version, repeated_item = _import_card(
        template=template,
        source_name="corrected-second.webp",
        checksum="corrected-faction-art",
        name="Corrected Faction Card",
    )

    original_version.card.refresh_from_db()
    assert original_item.resolved_card_factions_json == []
    assert original_item.warning_code == "evil_faction_unresolved"
    assert card_faction_keys(original_version.card) == ("order",)
    assert card_role_keys(original_version.card) == ("boss",)
    assert repeated_version.card_id == original_version.card_id
    assert repeated_item.target_card_id == original_version.card_id
    assert repeated_item.warning_code == "card_classification_mismatch"
    assert repeated_item.resolved_card_factions_json == []


@pytest.mark.django_db
def test_unknown_evil_faction_reuses_unique_name_after_artwork_changes() -> None:
    template = Template.objects.create(key="changed-art-import", label="Changed Art")
    original_version, _original_item = _import_card(
        template=template,
        source_name="changed-art-first.webp",
        checksum="changed-art-original",
        name="Changed Artwork Card",
    )
    change_card_identity(card=original_version.card, card_factions=("blood",))

    repeated_version, repeated_item = _import_card(
        template=template,
        source_name="changed-art-second.webp",
        checksum="changed-art-revised",
        name="Changed Artwork Card",
    )

    assert repeated_version.card_id == original_version.card_id
    assert repeated_version.version_number == 2
    assert repeated_item.warning_code == "card_classification_mismatch"
    assert card_faction_keys(repeated_version.card) == ("blood",)


@pytest.mark.django_db
def test_empty_evil_override_uses_unknown_faction_matching() -> None:
    template = Template.objects.create(key="empty-override-import", label="Empty Override")
    card, _created = create_card_identity(
        name="Empty Override Card",
        card_pool="evil",
        card_factions=("metal",),
    )
    evidence: CardClassificationInferenceEvidence = {
        "roles": {
            "mode": "automatic",
            "matched_tag_sources": [],
            "matched_type_sources": [],
            "matched_rules": [],
            "override_roles": [],
            "resolved_roles": [],
            "snapshot_digest": "override-test",
        },
        "factions": {
            "mode": "override",
            "matched_tag_sources": [],
            "matched_type_sources": [],
            "matched_rules": [],
            "override_factions": [],
            "resolved_factions": [],
            "snapshot_digest": "override-test",
        },
    }

    version, item = _import_card(
        template=template,
        source_name="empty-override.webp",
        checksum="empty-override-art",
        name="Empty Override Card",
        classification_evidence=evidence,
    )

    assert version.card_id == card.id
    assert item.warning_code == "card_classification_mismatch"
    assert item.classification_inference_json["factions"]["mode"] == "override"


@pytest.mark.django_db
def test_unknown_evil_faction_reuses_unique_alias_after_artwork_changes() -> None:
    template = Template.objects.create(key="alias-art-import", label="Alias Art")
    card, _created = create_card_identity(
        name="Current Card Name",
        card_pool="evil",
        card_factions=("dark",),
    )
    ensure_card_alias(card=card, key="old-card-name", label="Old Card Name")

    version, item = _import_card(
        template=template,
        source_name="alias-art.webp",
        checksum="alias-art-revised",
        name="Old Card Name",
    )

    assert version.card_id == card.id
    assert item.warning_code == "card_classification_mismatch"
    assert card_faction_keys(version.card) == ("dark",)


@pytest.mark.django_db
def test_unknown_evil_faction_matches_historical_image_version() -> None:
    template = Template.objects.create(key="historical-faction-import", label="Historical Faction")
    original_version, _original_item = _import_card(
        template=template,
        source_name="historical-original.webp",
        checksum="historical-faction-art",
        name="Historical Faction Card",
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

    repeated_version, repeated_item = _import_card(
        template=template,
        source_name="historical-repeat.webp",
        checksum="historical-faction-art",
        name="Historical Artwork Reimport",
    )

    assert repeated_version.card_id == original_version.card_id
    assert repeated_version.id not in {original_version.id, newer_version.id}
    assert repeated_version.version_number == 3
    assert repeated_version.previous_version_id == newer_version.id
    assert repeated_item.warning_code == "card_classification_mismatch"
    assert card_faction_keys(repeated_version.card) == ("dark",)


@pytest.mark.django_db
def test_unknown_evil_faction_refuses_ambiguous_image_candidates() -> None:
    template = Template.objects.create(key="ambiguous-image-import", label="Ambiguous Image")
    candidate_ids = set()
    for index, faction in enumerate(("order", "blood")):
        card, _created = create_card_identity(
            name=f"Shared Artwork {index}",
            card_pool="evil",
            card_factions=(faction,),
        )
        CardVersion.objects.create(
            card=card,
            template=template,
            image_hash="ambiguous-image-art",
            name=card.label,
        )
        candidate_ids.add(card.id)

    version, item = _import_card(
        template=template,
        source_name="ambiguous-image-new.webp",
        checksum="ambiguous-image-art",
        name="Independent Shared Artwork",
    )

    assert version.card_id not in candidate_ids
    assert card_faction_keys(version.card) == ()
    assert item.warning_code == "evil_faction_unresolved"
    assert item.warnings_json[0]["details"] == {
        "reason": "ambiguous_checksum",
        "checksum_candidate_count": 2,
        "name_candidate_count": 0,
    }


@pytest.mark.django_db
def test_unknown_evil_faction_refuses_ambiguous_name_candidates() -> None:
    template = Template.objects.create(key="ambiguous-name-import", label="Ambiguous Name")
    candidate_ids = {
        create_card_identity(
            name="Shared Evil Name",
            card_pool="evil",
            card_factions=(faction,),
        )[0].id
        for faction in ("order", "blood")
    }

    version, item = _import_card(
        template=template,
        source_name="ambiguous-name-new.webp",
        checksum="unique-new-art",
        name="Shared Evil Name",
    )

    assert version.card_id not in candidate_ids
    assert card_faction_keys(version.card) == ()
    assert item.warnings_json[0]["details"] == {
        "reason": "ambiguous_name",
        "checksum_candidate_count": 0,
        "name_candidate_count": 2,
    }


@pytest.mark.django_db
def test_unknown_evil_faction_refuses_conflicting_image_and_name() -> None:
    template = Template.objects.create(key="conflicting-match-import", label="Conflicting Match")
    image_card, _created = create_card_identity(
        name="Image Candidate",
        card_pool="evil",
        card_factions=("order",),
    )
    CardVersion.objects.create(
        card=image_card,
        template=template,
        image_hash="conflicting-match-art",
        name=image_card.label,
    )
    name_card, _created = create_card_identity(
        name="Name Candidate",
        card_pool="evil",
        card_factions=("blood",),
    )

    version, item = _import_card(
        template=template,
        source_name="conflicting-match-new.webp",
        checksum="conflicting-match-art",
        name="Name Candidate",
    )

    assert version.card_id not in {image_card.id, name_card.id}
    assert card_faction_keys(version.card) == ()
    assert item.warnings_json[0]["details"] == {
        "reason": "conflicting_evidence",
        "checksum_candidate_count": 1,
        "name_candidate_count": 1,
    }


@pytest.mark.django_db
def test_new_unknown_evil_faction_card_completes_with_actionable_warning() -> None:
    template = Template.objects.create(key="new-unknown-import", label="New Unknown")

    version, item = _import_card(
        template=template,
        source_name="new-unknown.webp",
        checksum="new-unknown-art",
        name="New Unknown Evil Card",
    )

    assert card_faction_keys(version.card) == ()
    assert item.warning_code == "evil_faction_unresolved"
    assert item.warning_message == "No Evil faction was inferred. Review and assign this Card's faction."
    assert item.warnings_json[0]["details"] == {
        "reason": "no_candidate",
        "checksum_candidate_count": 0,
        "name_candidate_count": 0,
    }


@pytest.mark.django_db
def test_unknown_evil_faction_prefers_existing_no_faction_namespace() -> None:
    template = Template.objects.create(key="existing-unknown-import", label="Existing Unknown")
    unresolved_version, _unresolved_item = _import_card(
        template=template,
        source_name="existing-unknown-first.webp",
        checksum="existing-unknown-first-art",
        name="Existing Unknown Card",
    )
    factioned_card, _created = create_card_identity(
        name="Existing Unknown Card",
        card_pool="evil",
        card_factions=("order",),
    )

    repeated_version, repeated_item = _import_card(
        template=template,
        source_name="existing-unknown-second.webp",
        checksum="existing-unknown-second-art",
        name="Existing Unknown Card",
    )

    assert repeated_version.card_id == unresolved_version.card_id
    assert repeated_version.card_id != factioned_card.id
    assert repeated_item.warnings_json[0]["details"] == {
        "reason": "existing_unresolved_card",
        "checksum_candidate_count": 0,
        "name_candidate_count": 0,
    }


@pytest.mark.django_db
def test_targeted_reparse_with_unknown_evil_faction_remains_targeted() -> None:
    template = Template.objects.create(key="targeted-unknown-import", label="Targeted Unknown")
    target_card, _created = create_card_identity(
        name="Targeted Unknown Card",
        card_pool="evil",
        card_factions=("order",),
    )
    target_version = CardVersion.objects.create(
        card=target_card,
        template=template,
        image_hash="targeted-unknown-art",
        name=target_card.label,
    )
    target_card.latest_version = target_version
    target_card.save(update_fields=["latest_version"])
    source_path = build_storage_relative_path("uploads", "faction-identity", "targeted.webp")
    path = settings.storage_root_dir / source_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"targeted-unknown-art")
    reparse_job = ImportJob.objects.create(
        source_path="uploads/faction-identity",
        template=template,
        card_pool="evil",
        total_items=1,
    )
    reparse_item = ImportJobItem.objects.create(
        job=reparse_job,
        source_file=source_path,
        target_card=target_card,
        target_card_version=target_version,
        target_card_pool_snapshot="evil",
        target_card_factions_snapshot_json=["order"],
    )
    save_parsed_card(
        item=reparse_item,
        template_id=template.key,
        checksum="targeted-unknown-art",
        normalized_fields={"name": "Targeted Unknown Card"},
        confidence={"overall": 1.0},
        raw_ocr={},
        card_pool="evil",
        resolved_card_factions=(),
    )
    reparse_item.refresh_from_db()
    assert reparse_item.warning_code == "card_classification_mismatch"
    assert all(
        warning["code"] != "evil_faction_unresolved"
        for warning in reparse_item.warnings_json
    )
    assert reparse_item.target_card_id == target_card.id


@pytest.mark.django_db
def test_disabled_reparse_keeps_unknown_evil_matching_disabled() -> None:
    template = Template.objects.create(key="disabled-match-import", label="Disabled Match")
    existing_card, _created = create_card_identity(
        name="Disabled Match Card",
        card_pool="evil",
        card_factions=("metal",),
    )

    version, item = _import_card(
        template=template,
        source_name="disabled-match.webp",
        checksum="disabled-match-art",
        name="Disabled Match Card",
        reparse_existing=False,
    )

    assert version.card_id != existing_card.id
    assert card_faction_keys(version.card) == ()
    assert item.warnings_json == []


@pytest.mark.django_db
@pytest.mark.parametrize("card_pool", ["player", "neutral"])
def test_unknown_faction_cross_namespace_matching_is_evil_only(card_pool: CardPool) -> None:
    template = Template.objects.create(
        key=f"{card_pool}-unknown-import",
        label=f"{card_pool.title()} Unknown",
    )
    existing_card, _created = create_card_identity(
        name="Other Pool Card",
        card_pool=card_pool,
        card_factions=("order",),
    )
    CardVersion.objects.create(
        card=existing_card,
        template=template,
        image_hash="other-pool-art",
        name=existing_card.label,
    )

    version, item = _import_card(
        template=template,
        source_name=f"{card_pool}-unknown.webp",
        checksum="other-pool-art",
        name="Other Pool Card",
        card_pool=card_pool,
    )

    assert version.card_id != existing_card.id
    assert card_faction_keys(version.card) == ()
    assert item.warnings_json == []


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
