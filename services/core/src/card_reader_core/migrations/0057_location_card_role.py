from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("card_reader_core", "0056_import_classification_inference")]

    operations = [
        migrations.AlterField(
            model_name="cardroleassignment",
            name="role",
            field=models.CharField(
                choices=[
                    ("hero", "Hero"),
                    ("boon", "Boon"),
                    ("event", "Event"),
                    ("location", "Location"),
                ],
                db_index=True,
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="importjob",
            name="card_role_inference_policy_version",
            field=models.IntegerField(default=2),
        ),
    ]
