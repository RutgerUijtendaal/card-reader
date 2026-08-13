from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db import IntegrityError, transaction
import pytest

from card_reader_core.config.settings import settings
from card_reader_core.models import (
    Card,
    CardAlias,
    CardBack,
    CardFactionAssignment,
    CardGroup,
    CardGroupMember,
    CardRoleAssignment,
    CardVersion,
    CardVersionImage,
    CardVersionKeyword,
    CardVersionSymbol,
    CardVersionTag,
    CardVersionType,
    ContentVersion,
    Deck,
    DeckTag,
    ImportJob,
    Keyword,
    MetadataSuggestion,
    ParseResult,
    Symbol,
    Tag,
    Template,
    TtsCardSheet,
    Type,
)
from card_reader_core.operations.developer_data import (
    DeveloperDataError,
    PublishedBundleStore,
    export_developer_data,
    import_developer_data,
    sha256_file,
    validate_archive,
)
from card_reader_core.operations.developer_data.importer import validate_import_readiness
from card_reader_core.operations.developer_data.schema import CardRecord, adopt_payload_for_format


def test_version_one_payload_adoption_maps_heroes_to_player_roles() -> None:
    adopted = adopt_payload_for_format(
        {"cards": [{"key": "hero", "is_hero": True}, {"key": "standard", "is_hero": False}]},
        format_version=1,
    )

    assert adopted == {
        "cards": [
            {
                "key": "hero",
                "card_pool": "player",
                "card_roles": ["hero"],
                "card_factions": [],
            },
            {
                "key": "standard",
                "card_pool": "player",
                "card_roles": [],
                "card_factions": [],
            },
        ]
    }


@pytest.mark.parametrize("legacy_card", [{"key": "missing"}, {"key": "wrong-type", "is_hero": "true"}])
def test_version_one_payload_adoption_rejects_invalid_hero_fields(
    legacy_card: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="is_hero must be a Boolean"):
        adopt_payload_for_format({"cards": [legacy_card]}, format_version=1)


def test_version_two_card_record_rejects_duplicate_roles() -> None:
    with pytest.raises(ValueError, match="Card roles must be unique"):
        CardRecord.model_validate(
            {
                "key": "duplicate-role-card",
                "label": "Duplicate Role Card",
                "card_pool": "player",
                "card_roles": ["hero", "hero"],
                "card_factions": [],
                "deck_building_config": {},
                "lifecycle_status": "active",
                "latest_version_number": None,
                "aliases": [],
                "versions": [],
            }
        )


def test_version_four_card_record_rejects_duplicate_factions() -> None:
    with pytest.raises(ValueError, match="Card factions must be unique"):
        CardRecord.model_validate(
            {
                "key": "duplicate-faction-card",
                "label": "Duplicate Faction Card",
                "card_pool": "evil",
                "card_roles": ["boss"],
                "card_factions": ["order", "order"],
                "deck_building_config": {},
                "lifecycle_status": "active",
                "latest_version_number": None,
                "aliases": [],
                "versions": [],
            }
        )


def test_version_two_payload_adoption_adds_empty_template_role_hints() -> None:
    adopted = adopt_payload_for_format(
        {"templates": [{"key": "legacy", "label": "Legacy", "definition": {}}]},
        format_version=2,
    )

    assert adopted == {
        "templates": [
            {
                "key": "legacy",
                "label": "Legacy",
                "definition": {},
                    "inferred_card_roles": [],
                    "inferred_card_factions": [],
            }
        ]
    }


def test_legacy_payload_adoption_namespaces_card_group_references() -> None:
    adopted = adopt_payload_for_format(
        {
            "cards": [
                {
                    "key": "legacy-card",
                    "card_pool": "player",
                    "card_roles": [],
                }
            ],
            "card_groups": [
                {
                    "key": "legacy-group",
                    "name": "Legacy Group",
                    "anchor_card_key": "legacy-card",
                    "members": [{"card_key": "legacy-card", "position": 1}],
                }
            ],
        },
        format_version=3,
    )

    reference = {
        "key": "legacy-card",
        "card_pool": "player",
        "card_factions": [],
    }
    assert adopted["card_groups"] == [  # type: ignore[index]
        {
            "key": "legacy-group",
            "name": "Legacy Group",
            "anchor_card_ref": reference,
            "members": [{"position": 1, "card_ref": reference}],
        }
    ]


def test_developer_data_coverage_rejects_missing_required_template_role_hint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_storage = tmp_path / "source-storage"
    selection_path = tmp_path / "selection.json"
    archive_path = tmp_path / "missing-template-role.tar.gz"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        selection = _build_synthetic_source(source_storage)
        template = Template.objects.get(key="synthetic-template")
        template.inferred_card_roles_json = []
        template.save(update_fields=["inferred_card_roles_json"])
        selection_path.write_text(json.dumps(selection), encoding="utf-8")

        with pytest.raises(DeveloperDataError, match="missing inference roles: event"):
            export_developer_data(
                selection_path=selection_path,
                output_path=archive_path,
                source_revision="missing-role-test",
            )
        transaction.set_rollback(True)


def test_synthetic_bundle_round_trip_reconstructs_allowlisted_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_storage = tmp_path / "source-storage"
    target_storage = tmp_path / "target-storage"
    archive_path = tmp_path / "synthetic-dev-data.tar.gz"
    selection_path = tmp_path / "selection.json"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        selection = _build_synthetic_source(source_storage)
        selection["include_all_cards"] = True
        selection_path.write_text(json.dumps(selection), encoding="utf-8")

        manifest = export_developer_data(
            selection_path=selection_path,
            output_path=archive_path,
            source_revision="synthetic-test-revision",
        )
        assert manifest.counts["cards"] == 4
        assert manifest.counts["card_versions"] == 5
        assert manifest.format_version == 4

        _, validated_payload = validate_archive(archive_path)
        mainboard_record = next(
            card for card in validated_payload.cards if card.key == "synthetic-mainboard"
        )
        mainboard_record.card_roles = ["boon"]
        assert "no active mainboard cards are included" not in validate_import_readiness(
            validated_payload
        )

        with tarfile.open(archive_path, "r:gz") as archive:
            data_member = archive.extractfile("data.json")
            assert data_member is not None
            payload_text = data_member.read().decode("utf-8")
        assert "raw_ocr_json" not in payload_text
        assert "source_file" not in payload_text
        assert '"card_pool"' in payload_text
        assert '"card_roles"' in payload_text
        assert '"card_factions"' in payload_text
        assert '"is_hero"' not in payload_text
        assert "synthetic-user" not in payload_text
        published_store = PublishedBundleStore(root=tmp_path / "published")
        published = published_store.publish(archive_path)
        assert published_store.current() == published
        with pytest.raises(DeveloperDataError, match="already published"):
            published_store.publish(archive_path)
        interrupted_root = tmp_path / "interrupted-publish"
        interrupted_root.mkdir()
        interrupted_target = interrupted_root / published.filename
        shutil.copy2(archive_path, interrupted_target)
        recovered_store = PublishedBundleStore(root=interrupted_root)
        recovered = recovered_store.publish(archive_path)
        assert recovered == published
        assert recovered_store.current() == published
        corrupt_archive = tmp_path / "corrupt-asset.tar.gz"
        _build_corrupt_asset_archive(
            archive_path,
            corrupt_archive,
            tmp_path / "corrupt-asset",
        )
        with pytest.raises(DeveloperDataError, match="checksum mismatch"):
            validate_archive(corrupt_archive)

        _clear_domain_data()
        DeckTag.objects.create(kind="role", key="control", label="Control")
        collision_archive = tmp_path / "alias-collision.tar.gz"
        _build_alias_collision_archive(archive_path, collision_archive, tmp_path / "collision")
        failed_storage = tmp_path / "failed-storage"
        monkeypatch.setattr(settings, "app_data_dir", failed_storage)
        with pytest.raises(IntegrityError):
            import_developer_data(archive_path=collision_archive)
        assert not any(path.is_file() for path in failed_storage.rglob("*"))
        assert not Card.objects.exists()

        monkeypatch.setattr(settings, "app_data_dir", target_storage)
        result = import_developer_data(
            archive_path=archive_path,
            expected_bundle_version="synthetic-v1",
            expected_archive_sha256=sha256_file(archive_path),
        )

        assert result.counts["cards"] == 4
        assert result.copied_assets == 7
        assert Card.objects.filter(key="synthetic-hero", role_assignments__role="hero").exists()
        assert Card.objects.filter(
            key="synthetic-deprecated", role_assignments__role="location"
        ).exists()
        assert CardAlias.objects.filter(key="synthetic-hero-alias").exists()
        assert CardGroup.objects.filter(key="synthetic-group").exists()
        assert Template.objects.get(key="synthetic-template").inferred_card_roles_json == ["event"]
        assert Template.objects.get(key="synthetic-template").inferred_card_factions_json == [
            "blood"
        ]
        assert set(
            Card.objects.get(
                key="synthetic-mainboard",
                faction_identity_key='["order","blood"]',
            )
            .faction_assignments.values_list("faction", flat=True)
        ) == {"order", "blood"}
        assert Card.objects.filter(key="synthetic-mainboard").count() == 2
        imported_group = CardGroup.objects.get(key="synthetic-group")
        assert imported_group.members.get(position=2).card.faction_identity_key == '["order","blood"]'
        latest = Card.objects.get(key="synthetic-hero").latest_version
        assert latest is not None
        assert latest.version_number == 2
        assert latest.card_version_keywords.filter(keyword__key="arrival").exists()
        assert latest.card_version_tags.filter(tag__key="synthetic").exists()
        assert latest.card_version_symbols.filter(symbol__key="arcane-mana").exists()
        assert latest.card_version_types.filter(type__key="creature").exists()
        assert Symbol.objects.get(key="arcane-mana").reference_assets_json == [
            "defaults/arcane.webp"
        ]
        assert (target_storage / "images" / "hero-v2.webp").read_bytes() == b"hero-v2"
        assert (target_storage / "symbols" / "defaults" / "arcane.webp").read_bytes() == b"symbol"

        with pytest.raises(DeveloperDataError, match="requires an empty domain database"):
            import_developer_data(archive_path=archive_path)
        transaction.set_rollback(True)


def test_bundle_selection_can_include_complete_card_and_group_catalogs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_storage = tmp_path / "source-storage"
    archive_path = tmp_path / "complete-catalog-dev-data.tar.gz"
    selection_path = tmp_path / "selection.json"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        selection = _build_synthetic_source(source_storage)
        Card.objects.create(key="additional-public-card", label="Additional Public Card")
        Card.objects.create(
            key="restricted-game-master-card",
            label="Restricted Evil Card",
            card_pool="evil",
        )
        Card.objects.create(
            key="synthetic-hero",
            label="Restricted Evil Twin",
            card_pool="evil",
        )
        Card.objects.create(
            key="synthetic-hero",
            label="Restricted Neutral Twin",
            card_pool="neutral",
        )
        selection.update(
            {
                "include_all_cards": True,
                "include_all_card_groups": True,
                "card_keys": [],
                "card_group_keys": [],
            }
        )
        selection_path.write_text(json.dumps(selection), encoding="utf-8")

        manifest = export_developer_data(
            selection_path=selection_path,
            output_path=archive_path,
            source_revision="complete-catalog-test-revision",
        )

        assert manifest.counts["cards"] == 5
        assert manifest.counts["card_groups"] == 1
        with tarfile.open(archive_path, "r:gz") as archive:
            data_member = archive.extractfile("data.json")
            assert data_member is not None
            payload = json.loads(data_member.read())
        assert {card["key"] for card in payload["cards"]} == {
            "additional-public-card",
            "synthetic-deprecated",
            "synthetic-hero",
            "synthetic-mainboard",
        }
        transaction.set_rollback(True)


def test_group_selection_keeps_same_key_faction_twins_out_of_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_storage = tmp_path / "source-storage"
    archive_path = tmp_path / "group-selection-dev-data.tar.gz"
    selection_path = tmp_path / "selection.json"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        selection = _build_synthetic_source(source_storage)
        selection.update(
            {
                "card_keys": ["synthetic-deprecated"],
                "card_group_keys": ["synthetic-group"],
                "coverage": {
                    **selection["coverage"],  # type: ignore[dict-item]
                    "min_cards": 3,
                    "min_cards_by_pool": {"player": 3, "evil": 0, "neutral": 0},
                },
            }
        )
        selection_path.write_text(json.dumps(selection), encoding="utf-8")

        manifest = export_developer_data(
            selection_path=selection_path,
            output_path=archive_path,
            source_revision="group-selection-test-revision",
        )

        assert manifest.counts["cards"] == 3
        _, payload = validate_archive(archive_path)
        mainboards = [card for card in payload.cards if card.key == "synthetic-mainboard"]
        assert [card.card_factions for card in mainboards] == [["order", "blood"]]
        transaction.set_rollback(True)


def test_explicit_card_selection_rejects_same_key_faction_twins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_storage = tmp_path / "source-storage"
    archive_path = tmp_path / "ambiguous-selection-dev-data.tar.gz"
    selection_path = tmp_path / "selection.json"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        selection = _build_synthetic_source(source_storage)
        selection.update(
            {
                "card_keys": ["synthetic-mainboard"],
                "card_group_keys": [],
            }
        )
        selection_path.write_text(json.dumps(selection), encoding="utf-8")

        with pytest.raises(
            DeveloperDataError,
            match=(
                "Selected card keys are ambiguous across faction namespaces: "
                "synthetic-mainboard"
            ),
        ):
            export_developer_data(
                selection_path=selection_path,
                output_path=archive_path,
                source_revision="ambiguous-selection-test-revision",
            )
        transaction.set_rollback(True)


def test_import_removes_assets_copied_before_asset_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_storage = tmp_path / "source-storage"
    target_storage = tmp_path / "target-storage"
    archive_path = tmp_path / "synthetic-dev-data.tar.gz"
    selection_path = tmp_path / "selection.json"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        selection = _build_synthetic_source(source_storage)
        selection_path.write_text(json.dumps(selection), encoding="utf-8")
        export_developer_data(
            selection_path=selection_path,
            output_path=archive_path,
            source_revision="asset-cleanup-test-revision",
        )

        _clear_domain_data()
        conflicting_asset = target_storage / "images" / "deprecated.webp"
        conflicting_asset.parent.mkdir(parents=True)
        conflicting_asset.write_bytes(b"conflicting-local-content")
        monkeypatch.setattr(settings, "app_data_dir", target_storage)

        with pytest.raises(DeveloperDataError, match="Conflicting local asset already exists"):
            import_developer_data(archive_path=archive_path)

        assert conflicting_asset.read_bytes() == b"conflicting-local-content"
        assert not (target_storage / "images" / "card-back.webp").exists()
        assert not Card.objects.exists()
        transaction.set_rollback(True)


@pytest.mark.parametrize(
    "absolute_path",
    [
        "/srv/card-reader/models/symbol-detector.bin",
        "/opt/card-reader/templates/basic-mana.json",
    ],
)
def test_export_rejects_arbitrary_absolute_posix_paths(
    absolute_path: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_storage = tmp_path / "source-storage"
    archive_path = tmp_path / "synthetic-dev-data.tar.gz"
    selection_path = tmp_path / "selection.json"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        selection = _build_synthetic_source(source_storage)
        template = Template.objects.get(key="synthetic-template")
        template.definition_json = {
            **template.definition_json,
            "model_location": absolute_path,
        }
        template.save(update_fields=["definition_json"])
        selection_path.write_text(json.dumps(selection), encoding="utf-8")

        with pytest.raises(DeveloperDataError, match="Forbidden absolute filesystem path"):
            export_developer_data(
                selection_path=selection_path,
                output_path=archive_path,
                source_revision="absolute-path-test-revision",
            )
        transaction.set_rollback(True)


@pytest.mark.parametrize(
    "credential_key",
    [
        "api_key",
        "database_password",
        "client_secret",
        "access_token",
    ],
)
def test_export_rejects_credential_shaped_fields(
    credential_key: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_storage = tmp_path / "source-storage"
    archive_path = tmp_path / "synthetic-dev-data.tar.gz"
    selection_path = tmp_path / "selection.json"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        selection = _build_synthetic_source(source_storage)
        template = Template.objects.get(key="synthetic-template")
        template.definition_json = {
            **template.definition_json,
            credential_key: "must-not-be-published",
        }
        template.save(update_fields=["definition_json"])
        selection_path.write_text(json.dumps(selection), encoding="utf-8")

        with pytest.raises(DeveloperDataError, match="Forbidden credential field"):
            export_developer_data(
                selection_path=selection_path,
                output_path=archive_path,
                source_revision="credential-field-test-revision",
            )
        transaction.set_rollback(True)


def test_import_rejects_unreferenced_manifest_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_storage = tmp_path / "source-storage"
    target_storage = tmp_path / "target-storage"
    archive_path = tmp_path / "synthetic-dev-data.tar.gz"
    unsafe_archive_path = tmp_path / "unsafe-dev-data.tar.gz"
    selection_path = tmp_path / "selection.json"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        selection = _build_synthetic_source(source_storage)
        selection_path.write_text(json.dumps(selection), encoding="utf-8")
        export_developer_data(
            selection_path=selection_path,
            output_path=archive_path,
            source_revision="unreferenced-asset-test-revision",
        )
        _build_archive_with_unreferenced_asset(
            archive_path,
            unsafe_archive_path,
            tmp_path / "unreferenced-asset",
        )

        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", target_storage)
        with pytest.raises(DeveloperDataError, match="manifest contains unreferenced assets"):
            import_developer_data(archive_path=unsafe_archive_path)
        assert not target_storage.exists()
        transaction.set_rollback(True)


def test_doctor_resolves_symbol_assets_and_honors_legacy_bundle_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_storage = tmp_path / "source-storage"
    selection_path = tmp_path / "selection.json"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        monkeypatch.setattr(settings, "developer_data_selection_file", selection_path)
        selection_path.write_text(
            json.dumps(_build_synthetic_source(source_storage)),
            encoding="utf-8",
        )
        for index in range(14):
            Card.objects.create(
                key=f"doctor-mainboard-{index}",
                label=f"Doctor Mainboard {index}",
            )
        get_user_model().objects.create_superuser(
            username="doctor-admin",
            password="doctor-test-password",
        )

        call_command("doctor_dev_data")
        template = Template.objects.get(key="synthetic-template")
        template.inferred_card_roles_json = []
        template.save(update_fields=["inferred_card_roles_json"])
        call_command("doctor_dev_data", source_format_version=2)
        with pytest.raises(CommandError, match="missing inference roles: event"):
            call_command("doctor_dev_data", source_format_version=3)
        Tag.objects.exclude(key="synthetic").delete()
        call_command("doctor_dev_data", source_format_version=1)
        transaction.set_rollback(True)


def test_archive_validation_rejects_unsafe_paths(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        payload = b"escape"
        member = tarfile.TarInfo("../outside.txt")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))

    with pytest.raises(DeveloperDataError, match="Unsafe developer-data archive path"):
        validate_archive(archive_path)


@pytest.mark.parametrize(
    ("card_key", "card_pool", "expected_error"),
    [
        ("synthetic-deprecated", "evil", "non-Player cards: synthetic-deprecated"),
        ("synthetic-deprecated", "neutral", "non-Player cards: synthetic-deprecated"),
        ("synthetic-mainboard", "evil", "cross-pool card groups: synthetic-group"),
    ],
)
def test_archive_validation_rejects_restricted_cards_and_cross_pool_groups(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    card_key: str,
    card_pool: str,
    expected_error: str,
) -> None:
    source_storage = tmp_path / "source-storage"
    archive_path = tmp_path / "synthetic-dev-data.tar.gz"
    restricted_archive_path = tmp_path / "restricted-dev-data.tar.gz"
    selection_path = tmp_path / "selection.json"

    with transaction.atomic():
        _clear_domain_data()
        monkeypatch.setattr(settings, "app_data_dir", source_storage)
        selection_path.write_text(json.dumps(_build_synthetic_source(source_storage)), encoding="utf-8")
        export_developer_data(
            selection_path=selection_path,
            output_path=archive_path,
            source_revision="restricted-archive-test-revision",
        )
        _build_reclassified_archive(
            archive_path,
            restricted_archive_path,
            tmp_path / "restricted-archive",
            card_key=card_key,
            card_pool=card_pool,
        )

        with pytest.raises(DeveloperDataError, match=expected_error):
            validate_archive(restricted_archive_path)
        transaction.set_rollback(True)


def _build_alias_collision_archive(source: Path, target: Path, extraction_root: Path) -> None:
    extraction_root.mkdir()
    with tarfile.open(source, "r:gz") as archive:
        archive.extractall(extraction_root, filter="data")
    data_path = extraction_root / "data.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    deprecated = next(card for card in payload["cards"] if card["key"] == "synthetic-deprecated")
    deprecated["aliases"].append({"key": "synthetic-hero-alias", "label": "Collision"})
    serialized = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    data_path.write_bytes(serialized)
    manifest_path = extraction_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data_entry = next(entry for entry in manifest["files"] if entry["path"] == "data.json")
    data_entry["sha256"] = hashlib.sha256(serialized).hexdigest()
    data_entry["size_bytes"] = len(serialized)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with tarfile.open(target, "w:gz") as archive:
        for path in sorted(extraction_root.rglob("*")):
            archive.add(path, arcname=path.relative_to(extraction_root).as_posix())


def _build_reclassified_archive(
    source: Path,
    target: Path,
    extraction_root: Path,
    *,
    card_key: str,
    card_pool: str,
) -> None:
    extraction_root.mkdir()
    with tarfile.open(source, "r:gz") as archive:
        archive.extractall(extraction_root, filter="data")
    data_path = extraction_root / "data.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    group_references = [
        reference
        for group in payload["card_groups"]
        for reference in [
            group["anchor_card_ref"],
            *(member["card_ref"] for member in group["members"]),
        ]
        if reference["key"] == card_key
    ]
    referenced_factions = group_references[0]["card_factions"] if group_references else None
    card = next(
        card
        for card in payload["cards"]
        if card["key"] == card_key
        and (referenced_factions is None or card["card_factions"] == referenced_factions)
    )
    card["card_pool"] = card_pool
    for reference in group_references:
        if reference["card_factions"] == card["card_factions"]:
            reference["card_pool"] = card_pool
    serialized = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    data_path.write_bytes(serialized)
    manifest_path = extraction_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data_entry = next(entry for entry in manifest["files"] if entry["path"] == "data.json")
    data_entry["sha256"] = hashlib.sha256(serialized).hexdigest()
    data_entry["size_bytes"] = len(serialized)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with tarfile.open(target, "w:gz") as archive:
        for path in sorted(extraction_root.rglob("*")):
            archive.add(path, arcname=path.relative_to(extraction_root).as_posix())


def _build_corrupt_asset_archive(source: Path, target: Path, extraction_root: Path) -> None:
    extraction_root.mkdir()
    with tarfile.open(source, "r:gz") as archive:
        archive.extractall(extraction_root, filter="data")
    asset_path = next((extraction_root / "assets").rglob("*.*"))
    asset_path.write_bytes(b"corrupted")
    with tarfile.open(target, "w:gz") as archive:
        for path in sorted(extraction_root.rglob("*")):
            archive.add(path, arcname=path.relative_to(extraction_root).as_posix())


def _build_archive_with_unreferenced_asset(
    source: Path,
    target: Path,
    extraction_root: Path,
) -> None:
    extraction_root.mkdir()
    with tarfile.open(source, "r:gz") as archive:
        archive.extractall(extraction_root, filter="data")
    asset_path = extraction_root / "assets" / "uploads" / "private.txt"
    asset_path.parent.mkdir(parents=True)
    content = b"not part of the public bundle"
    asset_path.write_bytes(content)
    manifest_path = extraction_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].append(
        {
            "path": "assets/uploads/private.txt",
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with tarfile.open(target, "w:gz") as archive:
        for path in sorted(extraction_root.rglob("*")):
            archive.add(path, arcname=path.relative_to(extraction_root).as_posix())


def _build_synthetic_source(storage_root: Path) -> dict[str, object]:
    assets = {
        "images/hero-v1.webp": b"hero-v1",
        "images/hero-v2.webp": b"hero-v2",
        "images/mainboard.webp": b"mainboard",
        "images/mainboard-darkness.webp": b"mainboard-darkness",
        "images/deprecated.webp": b"deprecated",
        "images/card-back.webp": b"card-back",
        "symbols/defaults/arcane.webp": b"symbol",
    }
    for relative_path, content in assets.items():
        path = storage_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    keyword = Keyword.objects.create(key="arrival", label="Arrival", identifiers_json=["arrival"])
    tag = Tag.objects.create(key="synthetic", label="Synthetic", identifiers_json=["synthetic"])
    required_inference_tags = (
        "hero",
        "boss",
        "location",
        "shop-item",
        "order",
        "blood",
        "darkness",
    )
    Tag.objects.bulk_create(
        [
            Tag(key=key, label=key.replace("-", " ").title(), identifiers_json=[key])
            for key in required_inference_tags
        ]
    )
    card_type = Type.objects.create(key="creature", label="Creature", identifiers_json=["creature"])
    symbol = Symbol.objects.create(
        key="arcane-mana",
        label="Arcane Mana",
        symbol_type="mana",
        detector_type="template",
        detection_config_json={},
        text_enrichment_json={},
        reference_assets_json=["defaults/arcane.webp"],
        text_token="{AM}",
        enabled=True,
    )
    template = Template.objects.create(
        key="synthetic-template",
        label="Synthetic Template",
        definition_json={"id": "synthetic-template", "version": 1, "regions": []},
        inferred_card_roles_json=["event"],
        inferred_card_factions_json=["blood"],
    )
    DeckTag.objects.create(kind="role", key="control", label="Control")
    content_version = ContentVersion.objects.create(
        version_number="1.0.0",
        base_version="1.0",
        major=1,
        minor=0,
        patch=0,
        description="Synthetic public fixture",
    )
    hero = Card.objects.create(
        key="synthetic-hero",
        label="Synthetic Hero",
        deck_building_config_json={"mainboard_card_count": {"value": 60}},
    )
    CardRoleAssignment.objects.create(card=hero, role="hero")
    hero_v1 = _create_version(
        card=hero,
        template=template,
        content_version=content_version,
        version_number=1,
        stored_path="images/hero-v1.webp",
        content=assets["images/hero-v1.webp"],
        is_latest=False,
    )
    hero_v2 = _create_version(
        card=hero,
        template=template,
        content_version=content_version,
        version_number=2,
        stored_path="images/hero-v2.webp",
        content=assets["images/hero-v2.webp"],
        previous_version=hero_v1,
    )
    hero.latest_version = hero_v2
    hero.save(update_fields=["latest_version"])
    parse_result = ParseResult.objects.create(
        card_version=hero_v2,
        raw_ocr_json={"private": "never export this OCR payload"},
        normalized_fields_json={},
        confidence_json={},
    )
    hero_v2.parse_result = parse_result
    hero_v2.save(update_fields=["parse_result"])
    CardAlias.objects.create(
        card=hero,
        card_pool=hero.card_pool,
        key="synthetic-hero-alias",
        label="Hero Alias",
    )
    CardVersionKeyword.objects.create(card_version=hero_v2, keyword=keyword)
    CardVersionTag.objects.create(card_version=hero_v2, tag=tag)
    CardVersionSymbol.objects.create(card_version=hero_v2, symbol=symbol)
    CardVersionType.objects.create(card_version=hero_v2, type=card_type)

    mainboard = Card.objects.create(
        key="synthetic-mainboard",
        label="Synthetic Mainboard",
        faction_identity_key='["order","blood"]',
    )
    CardFactionAssignment.objects.bulk_create(
        [
            CardFactionAssignment(card=mainboard, faction="order"),
            CardFactionAssignment(card=mainboard, faction="blood"),
        ]
    )
    mainboard_version = _create_version(
        card=mainboard,
        template=template,
        content_version=content_version,
        version_number=1,
        stored_path="images/mainboard.webp",
        content=assets["images/mainboard.webp"],
    )
    mainboard.latest_version = mainboard_version
    mainboard.save(update_fields=["latest_version"])
    darkness_mainboard = Card.objects.create(
        key="synthetic-mainboard",
        label="Synthetic Mainboard Darkness",
        faction_identity_key='["darkness"]',
    )
    CardFactionAssignment.objects.create(card=darkness_mainboard, faction="darkness")
    darkness_mainboard_version = _create_version(
        card=darkness_mainboard,
        template=template,
        content_version=content_version,
        version_number=1,
        stored_path="images/mainboard-darkness.webp",
        content=assets["images/mainboard-darkness.webp"],
    )
    darkness_mainboard.latest_version = darkness_mainboard_version
    darkness_mainboard.save(update_fields=["latest_version"])
    deprecated = Card.objects.create(
        key="synthetic-deprecated",
        label="Synthetic Deprecated",
        lifecycle_status="deprecated",
    )
    CardRoleAssignment.objects.create(card=deprecated, role="location")
    deprecated_version = _create_version(
        card=deprecated,
        template=template,
        content_version=content_version,
        version_number=1,
        stored_path="images/deprecated.webp",
        content=assets["images/deprecated.webp"],
    )
    deprecated.latest_version = deprecated_version
    deprecated.save(update_fields=["latest_version"])

    group = CardGroup.objects.create(key="synthetic-group", name="Synthetic Group", anchor_card=hero)
    CardGroupMember.objects.create(group=group, card=hero, position=1)
    CardGroupMember.objects.create(group=group, card=mainboard, position=2)
    card_back_content = assets["images/card-back.webp"]
    CardBack.objects.create(
        label="Synthetic Card Back",
        original_filename="card-back.webp",
        source_file="private/source/card-back.png",
        stored_path="images/card-back.webp",
        width=744,
        height=1039,
        checksum=hashlib.sha256(card_back_content).hexdigest(),
        is_current=True,
    )
    return {
        "bundle_version": "synthetic-v1",
        "card_keys": [hero.key, deprecated.key],
        "card_group_keys": [group.key],
        "coverage": {
            "min_cards": 3,
            "min_cards_by_pool": {"player": 3, "evil": 0, "neutral": 0},
            "min_cards_by_role": {
                "standard": 1,
                "hero": 1,
                "boon": 0,
                "event": 0,
                "location": 1,
                "boss": 0,
                "shop_item": 0,
            },
            "min_cards_by_faction": {"order": 1, "blood": 1, "darkness": 0},
            "min_deprecated_cards": 1,
            "min_card_groups": 1,
            "min_cards_with_multiple_versions": 1,
            "required_template_keys": [template.key],
            "required_tag_keys": list(required_inference_tags),
            "required_template_role_hints": {template.key: ["event"]},
            "required_template_faction_hints": {template.key: ["blood"]},
        },
    }


def _create_version(
    *,
    card: Card,
    template: Template,
    content_version: ContentVersion,
    version_number: int,
    stored_path: str,
    content: bytes,
    previous_version: CardVersion | None = None,
    is_latest: bool = True,
) -> CardVersion:
    version = CardVersion.objects.create(
        card=card,
        version_number=version_number,
        template=template,
        image_hash=hashlib.sha256(content).hexdigest(),
        name=card.label,
        type_line="Creature",
        mana_cost="{AM}",
        mana_symbols_json=["arcane-mana"],
        mana_value=1,
        attack=1,
        health=1,
        rules_text_raw="Arrival: draw a card.",
        rules_text_enriched="{KEYWORD:ARRIVAL}: draw a card.",
        rules_text="Arrival: draw a card.",
        confidence=1.0,
        field_sources_json={"name": "synthetic"},
        parsed_snapshot_json={"name": card.label},
        is_latest=is_latest,
        previous_version=previous_version,
        content_version=content_version,
    )
    CardVersionImage.objects.create(
        card_version=version,
        source_file=f"private/source/{Path(stored_path).name}",
        stored_path=stored_path,
        width=744,
        height=1039,
        checksum=hashlib.sha256(content).hexdigest(),
    )
    return version


def _clear_domain_data() -> None:
    TtsCardSheet.objects.all().delete()
    Deck.objects.all().delete()
    ImportJob.objects.all().delete()
    CardGroup.objects.all().delete()
    Card.objects.all().delete()
    CardBack.objects.all().delete()
    MetadataSuggestion.objects.all().delete()
    ContentVersion.objects.all().delete()
    DeckTag.objects.all().delete()
    Keyword.objects.all().delete()
    Symbol.objects.all().delete()
    Tag.objects.all().delete()
    Type.objects.all().delete()
    Template.objects.all().delete()
