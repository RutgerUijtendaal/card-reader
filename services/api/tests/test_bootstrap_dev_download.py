from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from urllib.request import Request

import pytest

from card_reader_api.management.commands import bootstrap_dev
from card_reader_core.operations.developer_data import DeveloperDataLock


def test_bootstrap_command_loads_in_a_fresh_process() -> None:
    api_dir = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [sys.executable, "manage.py", "help", "bootstrap_dev"],
        cwd=api_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("answer", ["y", "Y", "yes", " YES "])
def test_bootstrap_tts_prompt_accepts_explicit_confirmation(
    answer: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: answer)

    assert bootstrap_dev._should_generate_tts_sheets({}) is True


@pytest.mark.parametrize("answer", ["", "n", "no", "later"])
def test_bootstrap_tts_prompt_defaults_to_skipping(
    answer: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: answer)

    assert bootstrap_dev._should_generate_tts_sheets({}) is False


def test_bootstrap_tts_flags_bypass_the_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: pytest.fail("TTS prompt should have been bypassed."),
    )

    assert bootstrap_dev._should_generate_tts_sheets({"generate_tts_sheets": True}) is True
    assert bootstrap_dev._should_generate_tts_sheets({"skip_tts_sheets": True}) is False


def test_bootstrap_tts_prompt_skips_when_input_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_input(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", unavailable_input)

    assert bootstrap_dev._should_generate_tts_sheets({}) is False


class _Response:
    def __init__(self, content: bytes, *, status: int = 200) -> None:
        self.content = content
        self.status = status
        self.offset = 0

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            self.offset = len(self.content)
            return self.content
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def test_download_retries_with_the_same_token_and_resumes_partial_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"abcdef"
    lock = DeveloperDataLock(
        bundle_version="resume-v1",
        format_version=1,
        sha256=hashlib.sha256(content).hexdigest(),
        api_base_url="https://cards.example.test/api",
    )
    exchange_payload = json.dumps(
        {
            "download_token": "same-retry-token",
            "bundle": {
                "sha256": lock.sha256,
                "size_bytes": len(content),
                "download_url": "/developer-data/bundles/resume-v1/download",
            },
        }
    ).encode()
    responses = iter(
        [
            _Response(exchange_payload),
            _Response(content[:3]),
            _Response(content[3:], status=206),
        ]
    )
    requests: list[Request] = []

    def fake_urlopen(request: Request, timeout: int) -> _Response:
        assert timeout in {30, 120}
        requests.append(request)
        return next(responses)

    monkeypatch.setattr(bootstrap_dev, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(bootstrap_dev, "urlopen", fake_urlopen)
    stdout = SimpleNamespace(write=lambda _value: None)

    archive = bootstrap_dev._download_bundle(lock=lock, code="ABCDE", stdout=stdout)

    assert archive.read_bytes() == content
    download_requests = requests[1:]
    assert all(
        request.get_header("Authorization") == "DevData same-retry-token"
        for request in download_requests
    )
    assert download_requests[0].get_header("Range") is None
    assert download_requests[1].get_header("Range") == "bytes=3-"


def test_download_retries_when_final_replacement_is_temporarily_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"abcdef"
    temporary = tmp_path / "bundle.tar.gz.part"
    target = tmp_path / "bundle.tar.gz"
    responses = iter([_Response(content)])
    replacement_attempts = 0
    original_replace = Path.replace

    def fake_urlopen(_request: Request, timeout: int) -> _Response:
        assert timeout == 120
        return next(responses)

    def replace_with_transient_failure(source: Path, destination: Path) -> Path:
        nonlocal replacement_attempts
        replacement_attempts += 1
        if replacement_attempts == 1:
            raise OSError("bundle is temporarily locked")
        return original_replace(source, destination)

    monkeypatch.setattr(bootstrap_dev, "urlopen", fake_urlopen)
    monkeypatch.setattr(Path, "replace", replace_with_transient_failure)
    messages: list[str] = []
    stdout = SimpleNamespace(write=messages.append)

    archive = bootstrap_dev._download_bundle_with_retries(
        token="same-retry-token",
        download_url="https://cards.example.test/bundle.tar.gz",
        expected_size=len(content),
        target=target,
        temporary=temporary,
        stdout=stdout,
    )

    assert archive.read_bytes() == content
    assert replacement_attempts == 2
    assert messages == ["Download interrupted; retrying (1/3)."]
