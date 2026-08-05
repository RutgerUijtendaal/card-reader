from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a command with temporary and cache paths contained inside the repository."
    )
    parser.add_argument("--task-name", default="default")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    options = parser.parse_args()

    command = options.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("a command is required after --")

    repo_root = Path(__file__).resolve().parent.parent
    task_name = re.sub(r"[^A-Za-z0-9._-]", "-", options.task_name).strip("-") or "default"
    task_root = repo_root / ".tmp" / "codex" / task_name
    temp_root = task_root / "tmp"
    uv_cache_root = task_root / "uv-cache"
    pytest_base_temp = task_root / "pytest"
    pytest_cache_dir = task_root / "pytest-cache"

    for path in (
        task_root,
        temp_root,
        uv_cache_root,
        pytest_base_temp,
        pytest_cache_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)

    environment = os.environ.copy()
    environment.update(
        {
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
            "TMPDIR": str(temp_root),
            "UV_CACHE_DIR": str(uv_cache_root),
        }
    )
    pytest_options = (
        f"--basetemp={shlex.quote(str(pytest_base_temp))} "
        f"-o cache_dir={shlex.quote(str(pytest_cache_dir))}"
    )
    current_pytest_options = environment.get("PYTEST_ADDOPTS", "").strip()
    environment["PYTEST_ADDOPTS"] = " ".join(
        option for option in (pytest_options, current_pytest_options) if option
    )

    return subprocess.run(command, cwd=repo_root, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
