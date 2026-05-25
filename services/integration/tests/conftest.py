from __future__ import annotations

import logging
import shutil
from pathlib import Path
from collections.abc import Generator

import pytest

from catalog_seed import build_catalog_preflight, seed_integration_catalog
from runtime import configure_test_environment


@pytest.fixture(scope="session", autouse=True)
def integration_runtime() -> Path:
    runtime_root = configure_test_environment()

    import django
    from django.core.management import call_command

    django.setup()

    from card_reader_core.database.connection import initialize_database

    initialize_database()
    issues = build_catalog_preflight()
    if issues:
        raise RuntimeError("\n".join(issues))

    call_command("migrate", interactive=False, verbosity=0)
    return runtime_root


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


@pytest.fixture(autouse=True)
def reset_runtime(integration_runtime: Path) -> None:
    from django.core.management import call_command
    from django.db import connections

    connections.close_all()
    call_command("flush", interactive=False, verbosity=0)
    _clear_runtime_directories(integration_runtime)
    seed_integration_catalog()


def _clear_runtime_directories(runtime_root: Path) -> None:
    for child in runtime_root.iterdir():
        if child.name in {"card_reader.db", "logs"}:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
