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

VERSION_PATTERN = re.compile(r'(?m)^version\s*=\s*"[^"]+"$')


def validate_version(value: str) -> str:
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise SystemExit(f"Invalid version '{value}'. Expected semantic version like 0.1.8.")
    return value


def set_json_version(path: Path, version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def set_toml_version(path: Path, version: str) -> None:
    content = path.read_text(encoding="utf-8")
    updated, count = VERSION_PATTERN.subn(f'version = "{version}"', content, count=1)
    if count != 1:
        raise SystemExit(f"Could not update version in {path}")
    path.write_text(updated, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/set-version.py <version>")

    version = validate_version(sys.argv[1].strip())
    VERSION_FILE.write_text(f"{version}\n", encoding="utf-8")

    for path in JSON_VERSION_FILES:
        set_json_version(path, version)

    for path in TOML_VERSION_FILES:
        set_toml_version(path, version)

    print(f"Updated repo version to {version}")


if __name__ == "__main__":
    main()
