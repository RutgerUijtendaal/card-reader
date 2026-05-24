from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_STORAGE_ROOT = Path(tempfile.mkdtemp(prefix="card-reader-api-tests-"))
os.environ["CARD_READER_APP_DATA_DIR"] = str(TEST_STORAGE_ROOT)
os.environ["CARD_READER_ENV"] = "test"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "card_reader_api.project.settings")

import django  # noqa: E402
from card_reader_core.database.connection import initialize_database  # noqa: E402
from card_reader_core.models import Template  # noqa: E402
from django.core.management import call_command  # noqa: E402

initialize_database()
django.setup()


def _default_template_definition() -> dict[str, object]:
    return {
        "id": "mtg-like-v1",
        "version": 7,
        "regions": [
            {
                "region_id": "top_bar",
                "parser_type": "name_mana_cost",
                "cut_region": {"unit": "relative", "x": 0.04, "y": 0.02, "w": 0.92, "h": 0.07},
                "ocr_config": {},
            },
            {
                "region_id": "type_bar",
                "parser_type": "type_tag",
                "cut_region": {"unit": "relative", "x": 0.04, "y": 0.54, "w": 0.92, "h": 0.05},
                "ocr_config": {},
            },
            {
                "region_id": "rules_text",
                "parser_type": "rules_text",
                "cut_region": {"unit": "relative", "x": 0.07, "y": 0.6, "w": 0.86, "h": 0.32},
                "ocr_config": {},
            },
            {
                "region_id": "rules_text_fallback",
                "parser_type": "rules_text",
                "cut_region": {"unit": "relative", "x": 0.07, "y": 0.7, "w": 0.86, "h": 0.12},
                "ocr_config": {},
            },
            {
                "region_id": "bottom_left",
                "parser_type": "attack",
                "cut_region": {"unit": "relative", "x": 0.01, "y": 0.9, "w": 0.14, "h": 0.09},
                "ocr_config": {},
            },
            {
                "region_id": "bottom_middle",
                "parser_type": "affinity",
                "cut_region": {"unit": "relative", "x": 0.37, "y": 0.93, "w": 0.26, "h": 0.06},
                "ocr_config": {},
            },
            {
                "region_id": "bottom_right",
                "parser_type": "health",
                "cut_region": {"unit": "relative", "x": 0.85, "y": 0.9, "w": 0.14, "h": 0.08},
                "ocr_config": {},
            },
        ],
    }


call_command("migrate", interactive=False, verbosity=0)
Template.objects.update_or_create(
    key="mtg-like-v1",
    defaults={
        "label": "MTG Like V1",
        "definition_json": _default_template_definition(),
    },
)
