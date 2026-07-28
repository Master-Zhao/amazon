import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models

import apps.accounts.managers


def normalize_existing_emails(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    seen = {}
    for user in User.objects.all().order_by("pk"):
        normalized = user.email.strip().casefold()
        existing_pk = seen.get(normalized)
        if existing_pk is not None:
            raise RuntimeError(
                "Cannot normalize duplicate user emails "
                f"for users {existing_pk} and {user.pk}"
            )
        seen[normalized] = user.pk
        if user.email != normalized:
            User.objects.filter(pk=user.pk).update(email=normalized)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            normalize_existing_emails,
            migrations.RunPython.noop,
        ),
        migrations.AlterModelManagers(
            name="user",
            managers=[
                ("objects", apps.accounts.managers.UserManager()),
            ],
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("email"),
                name="sys_user_email_ci_uniq",
            ),
        ),
        migrations.CreateModel(
            name="AuthenticationAuditEvent",
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
                ("event", models.CharField(max_length=32)),
                ("outcome", models.CharField(max_length=32)),
                ("email_hash", models.CharField(blank=True, max_length=64)),
                ("request_id", models.CharField(max_length=128)),
                (
                    "ip_address",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "db_table": "audit_auth_event",
                "indexes": [
                    models.Index(
                        fields=["event", "created_at"],
                        name="audit_auth_event_time_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="RefreshTokenRecord",
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
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "rotated_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="accounts.refreshtokenrecord",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refresh_token_records",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "db_table": "sys_refresh_token",
                "indexes": [
                    models.Index(
                        fields=["user", "expires_at"],
                        name="sys_refresh_user_exp_idx",
                    )
                ],
            },
        ),
    ]
