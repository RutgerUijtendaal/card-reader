from __future__ import annotations

import logging

from database.connection import get_session, initialize_database
from seeds.keywords import keyword_table_has_rows, seed_keywords
from seeds.shared import SeedDefinition, SeedResult
from seeds.symbols import seed_symbols, symbol_table_has_rows
from seeds.templates import seed_templates, template_table_has_rows

logger = logging.getLogger(__name__)

SEED_REGISTRY: tuple[SeedDefinition, ...] = (
    SeedDefinition(name="keywords", model_has_rows=keyword_table_has_rows, run=seed_keywords),
    SeedDefinition(name="symbols", model_has_rows=symbol_table_has_rows, run=seed_symbols),
    SeedDefinition(name="templates", model_has_rows=template_table_has_rows, run=seed_templates),
)


def run_registered_seeds(*, force: bool = False) -> list[SeedResult]:
    initialize_database()
    results: list[SeedResult] = []
    with get_session() as session:
        for seed in SEED_REGISTRY:
            if not force and seed.model_has_rows(session):
                result = SeedResult(
                    name=seed.name,
                    skipped=True,
                    message="table already has rows",
                )
                results.append(result)
                continue

            created, updated = seed.run(session)
            result = SeedResult(
                name=seed.name,
                skipped=False,
                created=created,
                updated=updated,
                message="ok",
            )
            results.append(result)
            logger.info(
                "Seed finished. seed=%s created=%s updated=%s",
                seed.name,
                created,
                updated,
            )
    return results
