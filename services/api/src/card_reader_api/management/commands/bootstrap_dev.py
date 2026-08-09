from __future__ import annotations

import getpass
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from card_reader_core.config.settings import REPO_ROOT, settings
from card_reader_core.operations.developer_data import (
    DeveloperDataError,
    DeveloperDataLock,
    import_developer_data,
    sha256_file,
)
from card_reader_core.services.tts_card_sheets import TtsCardSheetService


class Command(BaseCommand):
    help = "Bootstrap an empty local development database from the pinned developer-data bundle."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--archive", help="Use an already-downloaded bundle instead of a website code.")
        parser.add_argument("--code", help="Bootstrap code; omit to enter it interactively.")
        parser.add_argument("--admin-username")
        parser.add_argument("--admin-password")

    def handle(self, *args: object, **options: object) -> None:
        if not settings.is_dev:
            raise CommandError("Developer-data bootstrap is disabled outside development environments.")
        lock = _load_lock(REPO_ROOT / "dev-data.lock.json")
        archive_option = _optional_string(options.get("archive"))
        archive_path = Path(archive_option).expanduser().resolve() if archive_option else None
        if archive_path is None:
            archive_path = _verified_cached_bundle(lock)
            if archive_path is None:
                code = _optional_string(options.get("code")) or input("Website bootstrap code: ").strip()
                archive_path = _download_bundle(lock=lock, code=code, stdout=self.stdout)
            else:
                self.stdout.write(
                    f"Using verified cached developer-data bundle {lock.bundle_version}."
                )
        username = (
            _optional_string(options.get("admin_username"))
            or os.getenv("CARD_READER_DEV_ADMIN_USERNAME", "").strip()
            or input("Local admin username: ").strip()
        )
        if not username:
            raise CommandError("A local admin username is required.")
        password = (
            _optional_string(options.get("admin_password"))
            or os.getenv("CARD_READER_DEV_ADMIN_PASSWORD", "")
            or getpass.getpass("Local admin password: ")
        )
        _validate_local_admin_password(username=username, password=password)
        try:
            result = import_developer_data(
                archive_path=archive_path,
                expected_bundle_version=lock.bundle_version,
                expected_archive_sha256=lock.sha256,
            )
        except (DeveloperDataError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        _create_or_update_local_admin(username=username, password=password)
        call_command("seed_notification_examples", "--username", username, stdout=self.stdout)
        sheet_result = TtsCardSheetService().reconcile_all(render=True)
        call_command("doctor_dev_data", stdout=self.stdout)
        self.stdout.write(
            self.style.SUCCESS(
                f"Bootstrapped developer-data bundle {result.bundle_version} "
                f"with {result.copied_assets} copied assets."
                f" Generated {sheet_result.affected_sheets} TTS card sheets."
            )
        )


def _load_lock(path: Path) -> DeveloperDataLock:
    try:
        return DeveloperDataLock.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CommandError(f"Developer-data lock file is invalid: {path}") from exc


def _download_bundle(*, lock: DeveloperDataLock, code: str, stdout: Any) -> Path:
    filename = f"card-reader-dev-data-{lock.bundle_version}.tar.gz"
    cache_root = REPO_ROOT / ".tmp" / "dev-data"
    cache_root.mkdir(parents=True, exist_ok=True)
    target = cache_root / filename
    temporary = target.with_suffix(target.suffix + ".part")
    if target.is_file() and sha256_file(target) == lock.sha256:
        stdout.write(f"Using verified cached developer-data bundle {lock.bundle_version}.")
        return target
    exchange_url = urljoin(lock.api_base_url.rstrip("/") + "/", "developer-data/grants/exchange")
    payload = json.dumps(
        {"code": code, "bundle_version": lock.bundle_version},
        separators=(",", ":"),
    ).encode("utf-8")
    exchange_request = Request(
        exchange_url,
        data=payload,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(exchange_request, timeout=30) as response:
            exchange = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = _http_error_detail(exc)
        raise CommandError(f"Bootstrap-code exchange failed: {detail}") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise CommandError(f"Bootstrap-code exchange failed: {exc}") from exc
    token = str(exchange.get("download_token", "")).strip()
    bundle = exchange.get("bundle")
    if not token or not isinstance(bundle, dict) or bundle.get("sha256") != lock.sha256:
        raise CommandError("Website returned bundle metadata that does not match the lock file.")
    download_path = str(bundle.get("download_url", "")).strip()
    expected_download_path = (
        f"/developer-data/bundles/{lock.bundle_version}/download"
    )
    if download_path != expected_download_path:
        raise CommandError("Website returned an unexpected developer-data download URL.")
    expected_size = int(bundle.get("size_bytes", 0))
    if expected_size <= 0:
        raise CommandError("Website returned an invalid developer-data bundle size.")
    download_url = urljoin(lock.api_base_url.rstrip("/") + "/", download_path.lstrip("/"))
    stdout.write(f"Downloading developer-data bundle {lock.bundle_version}...")
    last_error = "download did not complete"
    for attempt in range(1, 4):
        downloaded_size = temporary.stat().st_size if temporary.is_file() else 0
        if downloaded_size > expected_size:
            temporary.unlink()
            downloaded_size = 0
        if downloaded_size == expected_size:
            temporary.replace(target)
            return target
        headers = {"Authorization": f"DevData {token}", "Accept": "application/gzip"}
        if downloaded_size:
            headers["Range"] = f"bytes={downloaded_size}-"
        download_request = Request(download_url, headers=headers)
        try:
            with urlopen(download_request, timeout=120) as response:
                is_partial = response.status == 206 and downloaded_size > 0
                mode = "ab" if is_partial else "wb"
                with temporary.open(mode) as handle:
                    while chunk := response.read(1024 * 1024):
                        handle.write(chunk)
            if temporary.stat().st_size == expected_size:
                temporary.replace(target)
                return target
            last_error = (
                f"received {temporary.stat().st_size} of {expected_size} bytes"
            )
        except HTTPError as exc:
            last_error = _http_error_detail(exc)
        except (OSError, URLError) as exc:
            last_error = str(exc)
        if attempt < 3:
            stdout.write(f"Download interrupted; retrying ({attempt}/3).")
    raise CommandError(
        f"Developer-data download failed after 3 attempts: {last_error}. "
        f"Partial data remains at {temporary}."
    )


def _verified_cached_bundle(lock: DeveloperDataLock) -> Path | None:
    target = REPO_ROOT / ".tmp" / "dev-data" / (
        f"card-reader-dev-data-{lock.bundle_version}.tar.gz"
    )
    if target.is_file() and sha256_file(target) == lock.sha256:
        return target
    return None


def _create_or_update_local_admin(*, username: str, password: str) -> None:
    _validate_local_admin_password(username=username, password=password)
    user_model = get_user_model()
    with transaction.atomic():
        user: Any
        user, _created = user_model.objects.get_or_create(username=username)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()


def _validate_local_admin_password(*, username: str, password: str) -> None:
    if not password:
        raise CommandError("A local admin password is required.")
    user_model = get_user_model()
    prospective_user = user_model(username=username)
    try:
        validate_password(password, user=prospective_user)
    except Exception as exc:
        messages = getattr(exc, "messages", [str(exc)])
        raise CommandError("Local admin password is invalid: " + "; ".join(messages)) from exc


def _http_error_detail(exc: HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        return str(payload.get("detail") or exc.reason)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return str(exc.reason)


def _optional_string(value: object) -> str | None:
    compact = str(value or "").strip()
    return compact or None
