from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0008_card_version_field_sources_snapshot")]

    operations = [
        migrations.RemoveConstraint("cardversion", "ux_card_version_card_version"),
        migrations.RemoveConstraint("cardversionkeyword", "ux_card_version_keyword_pair"),
        migrations.RemoveConstraint("cardversionsymbol", "ux_card_version_symbol_pair"),
        migrations.RemoveConstraint("cardversiontag", "ux_card_version_tag_pair"),
        migrations.RemoveConstraint("cardversiontype", "ux_card_version_type_pair"),
        migrations.RemoveIndex("cardversion", "ix_card_version_card_latest"),
        migrations.AlterField(
            model_name="card",
            name="latest_version_id",
            field=models.ForeignKey(
                blank=True,
                db_column="latest_version_id",
                default=None,
                null=True,
                on_delete=models.SET_NULL,
                related_name="+",
                to="card_reader_core.cardversion",
            ),
        ),
        migrations.AlterField(
            model_name="cardversion",
            name="card_id",
            field=models.ForeignKey(
                db_column="card_id",
                on_delete=models.CASCADE,
                related_name="versions",
                to="card_reader_core.card",
            ),
        ),
        migrations.AlterField(
            model_name="cardversion",
            name="template_id",
            field=models.ForeignKey(
                db_column="template_id",
                on_delete=models.PROTECT,
                related_name="card_versions",
                to="card_reader_core.template",
                to_field="key",
            ),
        ),
        migrations.AlterField(
            model_name="cardversion",
            name="previous_version_id",
            field=models.ForeignKey(
                blank=True,
                db_column="previous_version_id",
                default=None,
                null=True,
                on_delete=models.SET_NULL,
                related_name="next_versions",
                to="card_reader_core.cardversion",
            ),
        ),
        migrations.AlterField(
            model_name="cardversionimage",
            name="card_version_id",
            field=models.ForeignKey(
                db_column="card_version_id",
                on_delete=models.CASCADE,
                related_name="images",
                to="card_reader_core.cardversion",
            ),
        ),
        migrations.AlterField(
            model_name="parseresult",
            name="card_version_id",
            field=models.ForeignKey(
                db_column="card_version_id",
                on_delete=models.CASCADE,
                related_name="parse_results",
                to="card_reader_core.cardversion",
            ),
        ),
        migrations.AlterField(
            model_name="cardversionkeyword",
            name="card_version_id",
            field=models.ForeignKey(
                db_column="card_version_id",
                on_delete=models.CASCADE,
                related_name="card_version_keywords",
                to="card_reader_core.cardversion",
            ),
        ),
        migrations.AlterField(
            model_name="cardversionkeyword",
            name="keyword_id",
            field=models.ForeignKey(
                db_column="keyword_id",
                on_delete=models.CASCADE,
                related_name="card_version_keywords",
                to="card_reader_core.keyword",
            ),
        ),
        migrations.AlterField(
            model_name="cardversionsymbol",
            name="card_version_id",
            field=models.ForeignKey(
                db_column="card_version_id",
                on_delete=models.CASCADE,
                related_name="card_version_symbols",
                to="card_reader_core.cardversion",
            ),
        ),
        migrations.AlterField(
            model_name="cardversionsymbol",
            name="symbol_id",
            field=models.ForeignKey(
                db_column="symbol_id",
                on_delete=models.CASCADE,
                related_name="card_version_symbols",
                to="card_reader_core.symbol",
            ),
        ),
        migrations.AlterField(
            model_name="cardversiontag",
            name="card_version_id",
            field=models.ForeignKey(
                db_column="card_version_id",
                on_delete=models.CASCADE,
                related_name="card_version_tags",
                to="card_reader_core.cardversion",
            ),
        ),
        migrations.AlterField(
            model_name="cardversiontag",
            name="tag_id",
            field=models.ForeignKey(
                db_column="tag_id",
                on_delete=models.CASCADE,
                related_name="card_version_tags",
                to="card_reader_core.tag",
            ),
        ),
        migrations.AlterField(
            model_name="cardversiontype",
            name="card_version_id",
            field=models.ForeignKey(
                db_column="card_version_id",
                on_delete=models.CASCADE,
                related_name="card_version_types",
                to="card_reader_core.cardversion",
            ),
        ),
        migrations.AlterField(
            model_name="cardversiontype",
            name="type_id",
            field=models.ForeignKey(
                db_column="type_id",
                on_delete=models.CASCADE,
                related_name="card_version_types",
                to="card_reader_core.type",
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField("card", "latest_version_id", "latest_version"),
                migrations.RenameField("cardversion", "card_id", "card"),
                migrations.RenameField("cardversion", "template_id", "template"),
                migrations.RenameField("cardversion", "previous_version_id", "previous_version"),
                migrations.RenameField("cardversionimage", "card_version_id", "card_version"),
                migrations.RenameField("parseresult", "card_version_id", "card_version"),
                migrations.RenameField("cardversionkeyword", "card_version_id", "card_version"),
                migrations.RenameField("cardversionkeyword", "keyword_id", "keyword"),
                migrations.RenameField("cardversionsymbol", "card_version_id", "card_version"),
                migrations.RenameField("cardversionsymbol", "symbol_id", "symbol"),
                migrations.RenameField("cardversiontag", "card_version_id", "card_version"),
                migrations.RenameField("cardversiontag", "tag_id", "tag"),
                migrations.RenameField("cardversiontype", "card_version_id", "card_version"),
                migrations.RenameField("cardversiontype", "type_id", "type"),
            ],
        ),
        migrations.AddIndex(
            model_name="cardversion",
            index=models.Index(fields=["card", "is_latest"], name="ix_card_version_card_latest"),
        ),
        migrations.AddConstraint(
            model_name="cardversion",
            constraint=models.UniqueConstraint(
                fields=("card", "version_number"),
                name="ux_card_version_card_version",
            ),
        ),
        migrations.AddConstraint(
            model_name="cardversionkeyword",
            constraint=models.UniqueConstraint(
                fields=("card_version", "keyword"),
                name="ux_card_version_keyword_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="cardversionsymbol",
            constraint=models.UniqueConstraint(
                fields=("card_version", "symbol"),
                name="ux_card_version_symbol_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="cardversiontag",
            constraint=models.UniqueConstraint(
                fields=("card_version", "tag"),
                name="ux_card_version_tag_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="cardversiontype",
            constraint=models.UniqueConstraint(
                fields=("card_version", "type"),
                name="ux_card_version_type_pair",
            ),
        ),
    ]
