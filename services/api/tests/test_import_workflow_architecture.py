from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
API_SOURCE = REPO_ROOT / "services" / "api" / "src" / "card_reader_api"
CORE_SOURCE = REPO_ROOT / "services" / "core" / "src" / "card_reader_core"
FRONTEND_SOURCE = REPO_ROOT / "frontend" / "src" / "features" / "import-jobs"


def test_upload_view_delegates_staging_and_cleanup_to_admission_seam() -> None:
    source = (API_SOURCE / "imports" / "views.py").read_text(encoding="utf-8")

    assert "ImportUploadAdmission().admit" in source
    for forbidden in ["shutil", "rmtree", "_discard_unclaimed", "_publish_upload_atomically"]:
        assert forbidden not in source


def test_reparse_callers_do_not_own_grouping_or_transactions() -> None:
    for path in [
        API_SOURCE / "templates" / "views.py",
        API_SOURCE / "maintenance" / "services.py",
    ]:
        source = path.read_text(encoding="utf-8")
        assert "queue_grouped_reparse_jobs" in source
        assert "create_import_job_with_files" not in source
        assert "transaction.atomic" not in source
        assert "grouped_sources" not in source


def test_import_job_repositories_do_not_depend_on_import_services() -> None:
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in (CORE_SOURCE / "repositories").rglob("*.py")
        if "card_reader_core.services.imports" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_controller_delegates_every_activity_trigger_to_one_coordinator() -> None:
    controller = (
        FRONTEND_SOURCE / "composables" / "useImportJobsController.ts"
    ).read_text(encoding="utf-8")
    activity = (
        FRONTEND_SOURCE / "composables" / "useImportActivity.ts"
    ).read_text(encoding="utf-8")

    assert "useImportActivity()" in controller
    assert "fetchImportJobs" not in controller
    assert "fetchOperationsQueuePage" not in controller
    assert "fetchImportJobDetail" not in controller
    assert "await refreshActivity();" in activity
    assert "onMounted(() => void refreshActivity())" in activity
    assert "void refreshActivity();" in activity
