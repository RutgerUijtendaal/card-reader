from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0004_templates")]

    operations = [
        migrations.RunSQL(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS card_version_search USING fts5(
                card_id UNINDEXED,
                card_version_id UNINDEXED,
                name,
                type_line,
                rules_text,
                mana_cost
            )
            """,
            reverse_sql="DROP TABLE IF EXISTS card_version_search",
        )
    ]
