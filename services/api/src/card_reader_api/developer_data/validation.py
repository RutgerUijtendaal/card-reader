from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

from card_reader_core.config.settings import REPO_ROOT
from card_reader_core.operations.developer_data import DeveloperDataError


def validate_temporary_import(
    *,
    archive_path: Path,
    bundle_version: str,
    archive_sha256: str,
) -> None:
    manage_py = REPO_ROOT / "services" / "api" / "manage.py"
    with tempfile.TemporaryDirectory(prefix="card-reader-dev-data-publish-") as temp_value:
        app_data = Path(temp_value) / "app-data"
        environment = os.environ.copy()
        environment.update(
            {
                "CARD_READER_APP_DATA_DIR": str(app_data),
                "CARD_READER_DATABASE_PATH": "validation.sqlite3",
                "CARD_READER_DEVELOPER_DATA_DIR": str(Path(temp_value) / "published"),
                "CARD_READER_DEVELOPER_DATA_ACCEL_REDIRECT_PREFIX": "",
            }
        )
        for command in (
            [sys.executable, str(manage_py), "migrate_card_reader"],
            [
                sys.executable,
                str(manage_py),
                "import_dev_data",
                str(archive_path),
                "--bundle-version",
                bundle_version,
                "--sha256",
                archive_sha256,
            ],
        ):
            result = subprocess.run(
                command,
                cwd=REPO_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip() or "unknown validation error"
                raise DeveloperDataError(f"Temporary developer-data import failed: {detail}")
