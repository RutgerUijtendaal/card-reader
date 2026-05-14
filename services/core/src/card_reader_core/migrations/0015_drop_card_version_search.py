from __future__ import annotations

from django.db import migrations


CREATE_CARD_VERSION_SEARCH_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS card_version_search USING fts5(
    card_id UNINDEXED,
    card_version_id UNINDEXED,
    name,
    type_line,
    rules_text,
    mana_cost
)
"""

DROP_CARD_VERSION_SEARCH_SQL = "DROP TABLE IF EXISTS card_version_search"


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0014_rule_text_enrichment")]

    operations = [
        migrations.RunSQL(
            sql=DROP_CARD_VERSION_SEARCH_SQL,
            reverse_sql=CREATE_CARD_VERSION_SEARCH_SQL,
        )
    ]
