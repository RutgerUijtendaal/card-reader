from __future__ import annotations

from pathlib import Path

from catalog_seed import load_catalog_bundle
from helpers import load_case, load_case_paths

CASES_DIR = Path(__file__).resolve().parent / "fixtures" / "parser_db_cases"


def test_cases_reference_known_catalog_entries() -> None:
    catalog = load_catalog_bundle()

    for case_path in load_case_paths(CASES_DIR):
        case = load_case(case_path)
        expected = case["expected"]

        assert case["input"]["template_key"] in catalog["template_keys"]
        assert set(expected["metadata"]["keywords"]).issubset(catalog["keyword_keys"])
        assert set(expected["metadata"]["tags"]).issubset(catalog["tag_keys"])
        assert set(expected["metadata"]["types"]).issubset(catalog["type_keys"])
        assert set(expected["metadata"]["symbols"]).issubset(catalog["symbol_keys"])
        assert set(expected["snapshot"]["metadata"]["keywords"]).issubset(catalog["keyword_keys"])
        assert set(expected["snapshot"]["metadata"]["tags"]).issubset(catalog["tag_keys"])
        assert set(expected["snapshot"]["metadata"]["types"]).issubset(catalog["type_keys"])
        assert set(expected["snapshot"]["metadata"]["symbols"]).issubset(catalog["symbol_keys"])
