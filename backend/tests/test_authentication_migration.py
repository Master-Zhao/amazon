import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_authentication_migration_upgrades_phase_one_user_without_rewriting_0001():
    executor = MigrationExecutor(connection)
    executor.migrate([("accounts", "0001_initial")])
    old_apps = executor.loader.project_state(
        [("accounts", "0001_initial")]
    ).apps
    old_user = old_apps.get_model("accounts", "User").objects.create(
        username="migration-user",
        email="Migration.User@Example.INVALID",
        password="!",
    )

    executor = MigrationExecutor(connection)
    executor.migrate([("accounts", "0002_authentication")])
    new_apps = executor.loader.project_state(
        [("accounts", "0002_authentication")]
    ).apps
    migrated_user = new_apps.get_model("accounts", "User").objects.get(
        pk=old_user.pk
    )

    assert migrated_user.email == "migration.user@example.invalid"
    table_names = connection.introspection.table_names()
    assert "sys_refresh_token" in table_names
    assert "audit_auth_event" in table_names
