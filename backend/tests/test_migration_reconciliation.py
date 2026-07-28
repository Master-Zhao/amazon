import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_permission_description_upgrade_preserves_existing_rows():
    executor = MigrationExecutor(connection)
    executor.migrate(
        [
            ("permissions", "0001_initial"),
            ("knowledge", None),
        ]
    )
    old_apps = executor.loader.project_state(
        [("permissions", "0001_initial")]
    ).apps
    permission_model = old_apps.get_model("permissions", "Permission")
    existing, _ = permission_model.objects.update_or_create(
        code="custom.existing",
        defaults={
            "name": "原有上传权限",
        },
    )

    executor = MigrationExecutor(connection)
    executor.migrate(
        [
            ("permissions", "0003_seed_permissions"),
            ("knowledge", "0002_seed_knowledge"),
        ]
    )
    new_apps = executor.loader.project_state(
        [
            ("permissions", "0003_seed_permissions"),
            ("knowledge", "0002_seed_knowledge"),
        ]
    ).apps
    upgraded_permission = new_apps.get_model(
        "permissions", "Permission"
    ).objects.get(pk=existing.pk)

    assert upgraded_permission.code == "custom.existing"
    assert upgraded_permission.name == "原有上传权限"
    assert upgraded_permission.description == ""
    assert (
        new_apps.get_model("permissions", "Permission")
        .objects.get(code="reports.upload")
        .description
        == "上传和重处理报表"
    )
    assert new_apps.get_model(
        "knowledge", "KnowledgeCategory"
    ).objects.count() == 6


@pytest.mark.django_db(transaction=True)
def test_reconciled_migration_graph_has_no_unapplied_leaf_migrations():
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

    refreshed = MigrationExecutor(connection)

    assert refreshed.migration_plan(refreshed.loader.graph.leaf_nodes()) == []
