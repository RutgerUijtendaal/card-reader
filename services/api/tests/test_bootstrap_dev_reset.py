from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def test_reset_requires_exact_confirmation_and_creates_safety_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_bootstrap_script()
    repository_root = tmp_path / "repo"
    storage_root = repository_root / "storage"
    database_path = repository_root / "card_reader.db"
    storage_root.mkdir(parents=True)
    (storage_root / "images").mkdir()
    (storage_root / "images" / "card.webp").write_bytes(b"card")
    database_path.write_bytes(b"database")
    monkeypatch.setattr(module, "REPO_ROOT", repository_root)
    monkeypatch.setattr(module, "DATABASE_PATH", database_path)
    monkeypatch.setattr(module.settings, "app_data_dir", storage_root)
    monkeypatch.setattr("builtins.input", lambda _prompt: "no")

    with pytest.raises(SystemExit, match="Reset cancelled"):
        module._reset_local_data()
    assert database_path.exists()
    assert (storage_root / "images" / "card.webp").exists()

    monkeypatch.setattr("builtins.input", lambda _prompt: "RESET")
    module._reset_local_data()

    assert not database_path.exists()
    assert not storage_root.exists()
    backups = list((repository_root / ".tmp" / "dev-data" / "reset-backups").glob("*.tar.gz"))
    assert len(backups) == 1


def test_reset_rejects_repository_root_as_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_bootstrap_script()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "DATABASE_PATH", tmp_path / "card_reader.db")
    monkeypatch.setattr(module.settings, "app_data_dir", tmp_path)

    with pytest.raises(SystemExit, match="unsafe reset target"):
        module._reset_local_data()


def _load_bootstrap_script() -> ModuleType:
    repository_root = Path(__file__).resolve().parents[3]
    script_path = repository_root / "scripts" / "bootstrap-dev.py"
    spec = importlib.util.spec_from_file_location("card_reader_bootstrap_dev_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
