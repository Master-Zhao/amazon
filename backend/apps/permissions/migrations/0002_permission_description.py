from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("permissions", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="permission",
            name="description",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
