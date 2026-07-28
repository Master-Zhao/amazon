import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection


@pytest.mark.django_db
def test_custom_user_is_created_by_initial_migration():
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="phase1-user",
        email="phase1@example.invalid",
        password="test-only-password",
    )

    assert user.pk is not None
    assert user_model._meta.db_table == "sys_user"
    assert not hasattr(user, "tenant_id")
    assert "sys_user" in connection.introspection.table_names()


@pytest.mark.django_db
def test_custom_user_email_is_unique():
    user_model = get_user_model()
    user_model.objects.create_user(
        username="first",
        email="unique@example.invalid",
        password="test-only-password",
    )

    with pytest.raises(IntegrityError):
        user_model.objects.create_user(
            username="second",
            email="unique@example.invalid",
            password="test-only-password",
        )
