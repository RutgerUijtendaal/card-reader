from pathlib import Path
from typing import Any

import pytest
from django.db.models.deletion import ProtectedError
from PIL import Image

from card_reader_core.config.settings import settings
from card_reader_core.models import Card, CardBack
from card_reader_core.services.card_backs import (
    clear_pool_default,
    get_pool_card_back_defaults,
    resolve_effective_card_backs,
    select_card_back_override,
    set_pool_default,
)
from card_reader_core.services.card_merges import merge_cards, preview_card_merge


@pytest.mark.django_db
def test_resolution_prefers_override_and_uses_bounded_queries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    django_assert_num_queries: Any,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    player_default = _create_usable_card_back("player-default")
    override = _create_usable_card_back("override")
    set_pool_default("player", player_default.id)
    inherited = Card.objects.create(key="inherited", label="Inherited", card_pool="player")
    overridden = Card.objects.create(
        key="overridden",
        label="Overridden",
        card_pool="player",
        card_back_override=override,
    )

    with django_assert_num_queries(2):
        resolved = resolve_effective_card_backs([inherited.id, overridden.id])

    assert resolved[inherited.id].source == "pool_default"
    assert resolved[inherited.id].card_back == player_default
    assert resolved[overridden.id].source == "override"
    assert resolved[overridden.id].card_back == override


@pytest.mark.django_db
def test_pool_change_keeps_override_and_changes_inheritance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    player_default = _create_usable_card_back("player-default")
    evil_default = _create_usable_card_back("evil-default")
    override = _create_usable_card_back("override")
    set_pool_default("player", player_default.id)
    set_pool_default("evil", evil_default.id)
    inherited = Card.objects.create(key="inherited", label="Inherited", card_pool="player")
    overridden = Card.objects.create(
        key="overridden",
        label="Overridden",
        card_pool="player",
        card_back_override=override,
    )

    inherited.card_pool = "evil"
    inherited.save(update_fields=["card_pool"])
    overridden.card_pool = "evil"
    overridden.save(update_fields=["card_pool"])
    resolved = resolve_effective_card_backs([inherited.id, overridden.id])

    assert resolved[inherited.id].card_back == evil_default
    assert resolved[overridden.id].card_back == override


@pytest.mark.django_db
def test_assignments_validate_files_and_protect_referenced_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    usable = _create_usable_card_back("usable")
    missing = CardBack.objects.create(
        label="Missing",
        original_filename="missing.png",
        source_file="uploads/missing.png",
        stored_path="images/missing.webp",
        width=63,
        height=88,
        checksum="missing",
    )

    assert select_card_back_override(usable.id) == usable
    assert select_card_back_override(None) is None
    with pytest.raises(ValueError, match="missing"):
        set_pool_default("evil", missing.id)
    set_pool_default("evil", usable.id)
    with pytest.raises(ProtectedError):
        usable.delete()
    override = _create_usable_card_back("protected-override")
    Card.objects.create(key="protected-override", label="Protected", card_back_override=override)
    with pytest.raises(ProtectedError):
        override.delete()


@pytest.mark.django_db
def test_defaults_explicitly_include_missing_pools() -> None:
    assert get_pool_card_back_defaults() == {
        "player": None,
        "evil": None,
        "neutral": None,
    }


@pytest.mark.django_db
def test_pool_default_can_be_cleared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    card_back = _create_usable_card_back("default")
    set_pool_default("player", card_back.id)

    clear_pool_default("player")

    assert get_pool_card_back_defaults()["player"] is None


@pytest.mark.django_db
def test_merge_warns_about_different_overrides_and_preserves_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_data_dir", tmp_path)
    target_back = _create_usable_card_back("merge-target")
    source_back = _create_usable_card_back("merge-source")
    target = Card.objects.create(
        key="merge-target",
        label="Merge Target",
        card_back_override=target_back,
    )
    source = Card.objects.create(
        key="merge-source",
        label="Merge Source",
        card_back_override=source_back,
    )

    preview = preview_card_merge(target_card_id=target.id, source_card_ids=[source.id])
    merge_cards(target_card_id=target.id, source_card_ids=[source.id])

    assert preview.warnings == [
        "Card-back overrides differ; the target Card's override will be preserved.",
    ]
    target.refresh_from_db()
    assert target.card_back_override_id == target_back.id


def _create_usable_card_back(label: str) -> CardBack:
    stored_path = f"images/{label}.webp"
    path = settings.storage_root_dir / stored_path
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (63, 88), color=(20, 40, 90)).save(path, format="WEBP")
    return CardBack.objects.create(
        label=label,
        original_filename=f"{label}.png",
        source_file=f"uploads/{label}.png",
        stored_path=stored_path,
        width=63,
        height=88,
        checksum=label,
    )
