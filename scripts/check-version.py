#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO_ROOT / "VERSION"

JSON_VERSION_FILES = [
    REPO_ROOT / "apps" / "web" / "package.json",
    REPO_ROOT / "apps" / "desktop" / "package.json",
    REPO_ROOT / "apps" / "desktop" / "src-tauri" / "tauri.conf.json",
    REPO_ROOT / "services" / "api" / "package.json",
    REPO_ROOT / "services" / "core" / "package.json",
    REPO_ROOT / "services" / "integration" / "package.json",
    REPO_ROOT / "services" / "parser" / "package.json",
]

TOML_VERSION_FILES = [
    REPO_ROOT / "services" / "api" / "pyproject.toml",
    REPO_ROOT / "services" / "core" / "pyproject.toml",
    REPO_ROOT / "services" / "integration" / "pyproject.toml",
    REPO_ROOT / "services" / "parser" / "pyproject.toml",
    REPO_ROOT / "apps" / "desktop" / "src-tauri" / "Cargo.toml",
]

VERSION_PATTERN = re.compile(r'(?m)^version\s*=\s*"([^"]+)"$')


def read_repo_version() -> str:
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"Invalid VERSION contents: '{version}'")
    return version


def read_json_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str):
        raise SystemExit(f"Missing string version in {path}")
    return version


def read_toml_version(path: Path) -> str:
    match = VERSION_PATTERN.search(path.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"Missing version field in {path}")
    return match.group(1)


def main() -> None:
    expected = read_repo_version()
    mismatches: list[str] = []

    for path in JSON_VERSION_FILES:
        actual = read_json_version(path)
        if actual != expected:
            mismatches.append(f"{path.relative_to(REPO_ROOT)}: expected {expected}, found {actual}")

    for path in TOML_VERSION_FILES:
        actual = read_toml_version(path)
        if actual != expected:
            mismatches.append(f"{path.relative_to(REPO_ROOT)}: expected {expected}, found {actual}")

    if mismatches:
        print("Version mismatch detected:")
        for mismatch in mismatches:
            print(f"- {mismatch}")
        raise SystemExit(1)

    print(f"All manifest versions match VERSION={expected}")


if __name__ == "__main__":
    main()
