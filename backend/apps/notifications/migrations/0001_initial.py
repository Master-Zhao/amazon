import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0002_authentication"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("SYSTEM", "System"),
                            ("ANALYSIS_COMPLETE", "Analysis Complete"),
                            ("APPROVAL_REQUIRED", "Approval Required"),
                            ("ACTION_EXECUTED", "Action Executed"),
                            ("REPORT_IMPORTED", "Report Imported"),
                            ("ANOMALY_DETECTED", "Anomaly Detected"),
                        ],
                        default="SYSTEM",
                        max_length=32,
                    ),
                ),
                ("title", models.CharField(max_length=256)),
                ("content", models.TextField(blank=True)),
                ("target_route", models.CharField(blank=True, max_length=512)),
                ("is_read", models.BooleanField(default=False)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notifications",
                        to="tenants.tenant",
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "sys_notification",
                "indexes": [
                    models.Index(
                        fields=["recipient", "-created_at"],
                        name="sys_notif_rec_cr_idx",
                    ),
                    models.Index(
                        fields=["recipient", "is_read"],
                        name="sys_notif_rec_rd_idx",
                    ),
                    models.Index(
                        fields=["tenant", "-created_at"],
                        name="sys_notif_tn_cr_idx",
                    ),
                ],
            },
        ),
    ]