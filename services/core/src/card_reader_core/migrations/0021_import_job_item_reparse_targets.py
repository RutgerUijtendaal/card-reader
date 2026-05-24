from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0020_card_hero_and_decks")]

    operations = [
        migrations.AddField(
            model_name="importjobitem",
            name="target_card",
            field=models.ForeignKey(
                blank=True,
                db_column="target_card_id",
                default=None,
                null=True,
                on_delete=models.SET_NULL,
                related_name="+",
                to="card_reader_core.card",
            ),
        ),
        migrations.AddField(
            model_name="importjobitem",
            name="target_card_version",
            field=models.ForeignKey(
                blank=True,
                db_column="target_card_version_id",
                default=None,
                null=True,
                on_delete=models.SET_NULL,
                related_name="+",
                to="card_reader_core.cardversion",
            ),
        ),
    ]
