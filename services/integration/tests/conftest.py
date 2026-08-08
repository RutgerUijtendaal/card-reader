from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from card_reader_core.config.settings import settings as core_settings
from catalog_seed import (
    build_catalog_preflight,
    check_ocr_runtime,
    seed_integration_catalog,
)

if TYPE_CHECKING:
    from card_reader_parser.parsers.card_parser import CardParser
    from card_reader_parser.parsers.ocr_runner import OcrRunner


@pytest.fixture(autouse=True)
def isolate_integration_test_state(
    db: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(core_settings, "app_data_dir", tmp_path)
    seed_integration_catalog()


@pytest.fixture(scope="session", autouse=True)
def integration_ocr_runner() -> OcrRunner:
    from card_reader_parser.parsers.ocr_runner import OcrRunner

    issues = build_catalog_preflight()
    if issues:
        raise RuntimeError("\n".join(issues))

    runner = OcrRunner()
    issues = check_ocr_runtime(runner)
    if issues:
        raise RuntimeError("\n".join(issues))
    return runner


@pytest.fixture(scope="session")
def integration_card_parser(integration_ocr_runner: OcrRunner) -> CardParser:
    from card_reader_parser.parsers.card_parser import CardParser

    return CardParser(ocr_runner=integration_ocr_runner)


@pytest.fixture(scope="session", autouse=True)
def integration_logging(tmp_path_factory: pytest.TempPathFactory) -> Generator[None, None, None]:
    logs_dir = tmp_path_factory.mktemp("integration-logs")
    log_file = logs_dir / "integration-tests.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    previous_level = root_logger.level
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    try:
        yield
    finally:
        root_logger.removeHandler(file_handler)
        root_logger.setLevel(previous_level)
        file_handler.close()
