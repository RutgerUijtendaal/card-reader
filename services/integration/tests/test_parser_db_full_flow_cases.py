from __future__ import annotations

import json
from pathlib import Path

import pytest

from helpers import assert_recursive_exact, case_id, load_case_paths, run_case

CASES_DIR = Path(__file__).resolve().parent / "fixtures" / "parser_db_cases"


@pytest.mark.parametrize("case_path", load_case_paths(CASES_DIR), ids=case_id)
def test_parser_db_full_flow_with_real_ocr(case_path: Path) -> None:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    db_state = run_case(case_path)
    assert_recursive_exact(case["expected_db"], db_state)
