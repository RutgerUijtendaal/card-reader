from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0064_card_back_import_receipt")]

    operations = [
        migrations.AddField(
            model_name="importjobitem",
            name="attempt_count",
            field=models.PositiveIntegerField(default=0, db_default=0),
        ),
    ]
