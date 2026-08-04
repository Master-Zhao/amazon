from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdvertisingProfileRemoteScope",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("external_merchant_id", models.CharField(max_length=128)),
                ("merchant_code", models.CharField(max_length=128)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "profile",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="remote_scope",
                        to="stores.advertisingprofile",
                    ),
                ),
            ],
            options={
                "db_table": "ads_profile_remote_scope",
                "indexes": [
                    models.Index(
                        fields=["is_active", "merchant_code"],
                        name="ads_profile_remote_active_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("external_merchant_id", "merchant_code"),
                        name="ads_profile_remote_scope_uniq",
                    )
                ],
            },
        ),
    ]
