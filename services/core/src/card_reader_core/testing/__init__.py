"""Test support shared by Card Reader's Python service suites."""

from .sqlite_baseline import SqliteTestBaseline, mark_sqlite_test_storage

__all__ = ["SqliteTestBaseline", "mark_sqlite_test_storage"]
