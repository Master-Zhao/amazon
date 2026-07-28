import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class CreateModelIfMissing(migrations.CreateModel):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        table_name = "action_effect_evaluation"
        if table_name in schema_editor.connection.introspection.table_names():
            return
        super().database_forwards(
            app_label,
            schema_editor,
            from_state,
            to_state,
        )

    def database_backwards(
        self,
        app_label,
        schema_editor,
        from_state,
        to_state,
    ):
        # A compatibility rollback never removes a pre-existing business table.
        pass

    def describe(self):
        return "Create action_effect_evaluation only when it is absent"


class Migration(migrations.Migration):
    dependencies = [
        ("actions", "0002_initial"),
        ("stores", "0001_initial"),
        ("tenants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        CreateModelIfMissing(
                    name="EffectEvaluation",
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
                        ("status", models.CharField(max_length=32)),
                        ("baseline_start", models.DateField()),
                        ("baseline_end", models.DateField()),
                        ("observation_start", models.DateField()),
                        ("observation_end", models.DateField()),
                        (
                            "celery_task_id",
                            models.CharField(max_length=128, unique=True),
                        ),
                        (
                            "idempotency_key",
                            models.CharField(max_length=128, unique=True),
                        ),
                        ("result", models.JSONField(default=dict)),
                        (
                            "reason_code",
                            models.CharField(blank=True, max_length=96),
                        ),
                        ("error_message", models.TextField(blank=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "started_at",
                            models.DateTimeField(blank=True, null=True),
                        ),
                        (
                            "finished_at",
                            models.DateTimeField(blank=True, null=True),
                        ),
                        (
                            "execution_record",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="effect_evaluations",
                                to="actions.executionrecord",
                            ),
                        ),
                        (
                            "profile",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="effect_evaluations",
                                to="stores.advertisingprofile",
                            ),
                        ),
                        (
                            "requested_by",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="effect_evaluations",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "tenant",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="effect_evaluations",
                                to="tenants.tenant",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "action_effect_evaluation",
                        "indexes": [
                            models.Index(
                                fields=[
                                    "tenant",
                                    "profile",
                                    "status",
                                    "created_at",
                                ],
                                name="action_effect_scope_status_idx",
                            )
                        ],
                        "constraints": [
                            models.UniqueConstraint(
                                fields=(
                                    "execution_record",
                                    "baseline_start",
                                    "baseline_end",
                                    "observation_start",
                                    "observation_end",
                                ),
                                name="action_effect_window_uniq",
                            )
                        ],
                    },
        )
    ]
