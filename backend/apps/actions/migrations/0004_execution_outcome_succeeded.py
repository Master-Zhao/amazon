from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("actions", "0003_effect_evaluation")]

    operations = [
        migrations.AlterField(
            model_name="executionrecord",
            name="outcome",
            field=models.CharField(
                choices=[
                    ("SUCCEEDED", "Succeeded"),
                    ("SUCCESS", "Success (legacy)"),
                    ("FAILED", "Failed"),
                    ("SKIPPED", "Skipped"),
                ],
                max_length=16,
            ),
        ),
    ]
