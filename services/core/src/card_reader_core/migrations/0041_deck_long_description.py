from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0040_seed_new_player_deck_tag")]

    operations = [
        migrations.AddField(
            model_name="deck",
            name="long_description",
            field=models.TextField(blank=True, default=None, null=True),
        ),
    ]
