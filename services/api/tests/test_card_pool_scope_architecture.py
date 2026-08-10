from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
API_SOURCE = REPO_ROOT / "services" / "api" / "src" / "card_reader_api"
CORE_SOURCE = REPO_ROOT / "services" / "core" / "src" / "card_reader_core"


def _python_source(root: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts
    )


def test_card_payloads_do_not_restore_boolean_game_master_flags() -> None:
    assert "allow_game_master_cards" not in _python_source(API_SOURCE)
    assert "allow_game_master_cards" not in _python_source(CORE_SOURCE)


def test_game_master_entitlement_is_only_consumed_by_the_auth_mapper() -> None:
    direct_consumers: list[str] = []
    auth_path = API_SOURCE / "common" / "auth_access.py"
    for path in sorted(API_SOURCE.rglob("*.py")):
        if path == auth_path:
            continue
        if "can_access_game_master_cards" in path.read_text(encoding="utf-8"):
            direct_consumers.append(path.relative_to(REPO_ROOT).as_posix())

    assert direct_consumers == []


def test_card_http_surfaces_do_not_read_staff_policy_directly() -> None:
    scoped_roots = (
        API_SOURCE / "cards",
        API_SOURCE / "card_groups",
        API_SOURCE / "decks",
        API_SOURCE / "exports",
    )
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for root in scoped_roots
        for path in sorted(root.rglob("*.py"))
        if "user.is_staff" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_public_artifact_modules_do_not_request_all_pool_scope() -> None:
    public_artifact_paths = (
        CORE_SOURCE / "operations" / "developer_data",
        CORE_SOURCE / "repositories" / "tts_card_sheets",
        CORE_SOURCE / "services" / "tts_card_sheets",
        CORE_SOURCE / "services" / "exports",
    )
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for root in public_artifact_paths
        for path in sorted(root.rglob("*.py"))
        if "ALL_CARD_POOLS_SCOPE" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_secure_card_views_use_scoped_identity_lookups() -> None:
    source = (API_SOURCE / "cards" / "views.py").read_text(encoding="utf-8")

    assert "get_card(" not in source
    assert "get_card_with_image(" not in source
    assert "list_card_generations(" not in source
