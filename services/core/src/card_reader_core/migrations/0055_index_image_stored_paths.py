from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0054_card_classification")]

    operations = [
        migrations.AlterField(
            model_name="cardback",
            name="stored_path",
            field=models.TextField(db_index=True),
        ),
        migrations.AlterField(
            model_name="cardversionimage",
            name="stored_path",
            field=models.TextField(db_index=True),
        ),
    ]
