from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from runtime import cleanup_test_environment, configure_test_environment

INTEGRATION_RUNTIME_ROOT = configure_test_environment()

from catalog_seed import (  # noqa: E402
    build_catalog_preflight,
    check_ocr_runtime,
    seed_integration_catalog,
)

if TYPE_CHECKING:
    from card_reader_core.testing import SqliteTestBaseline
    from card_reader_parser.parsers.card_parser import CardParser
    from card_reader_parser.parsers.ocr_runner import OcrRunner


@pytest.fixture(scope="session", autouse=True)
def integration_runtime() -> Generator[Path, None, None]:
    runtime_root = INTEGRATION_RUNTIME_ROOT

    try:
        import django
        from django.core.management import call_command

        django.setup()

        from card_reader_core.database.connection import initialize_database

        initialize_database()
        issues = build_catalog_preflight()
        if issues:
            raise RuntimeError("\n".join(issues))

        call_command("migrate", interactive=False, verbosity=0)
        seed_integration_catalog()
        yield runtime_root
    finally:
        from django.db import connections

        connections.close_all()
        cleanup_test_environment()


@pytest.fixture(scope="session", autouse=True)
def integration_ocr_runner(integration_runtime: Path) -> OcrRunner:
    from card_reader_parser.parsers.ocr_runner import OcrRunner

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
def integration_logging(integration_runtime: Path) -> Generator[None, None, None]:
    logs_dir = integration_runtime / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
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


@pytest.fixture(scope="session")
def integration_test_baseline(
    integration_runtime: Path,
) -> Generator[SqliteTestBaseline, None, None]:
    from card_reader_core.testing import SqliteTestBaseline, mark_sqlite_test_storage

    mark_sqlite_test_storage(integration_runtime)
    baseline = SqliteTestBaseline(
        storage_root=integration_runtime,
        preserved_runtime_names={"logs"},
    )
    try:
        yield baseline
    finally:
        baseline.close()


@pytest.fixture(autouse=True)
def isolate_integration_test_state(
    integration_test_baseline: SqliteTestBaseline,
) -> Generator[None, None, None]:
    yield
    integration_test_baseline.restore()
