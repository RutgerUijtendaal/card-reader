from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0041_deck_long_description")]

    operations = [
        migrations.AddField(
            model_name="deck",
            name="difficulty",
            field=models.CharField(
                blank=True,
                choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")],
                default=None,
                max_length=16,
                null=True,
            ),
        ),
    ]
