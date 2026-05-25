from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0022_deck_sideboards")]

    operations = [
        migrations.AddConstraint(
            model_name="decksideboardentry",
            constraint=models.UniqueConstraint(
                fields=("sideboard", "card"),
                name="ux_deck_sideboard_entry_card",
            ),
        ),
    ]
