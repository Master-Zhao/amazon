import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.permissions.models import Permission
from apps.stores.models import AdvertisingProfile, AmazonStore
from apps.tenants.models import Tenant, TenantMembership


@pytest.mark.django_db(transaction=True)
def test_demo_seed_commands_are_idempotent_and_restore_a_usable_account():
    email = "seed-verifier@example.invalid"
    password = "test-only-seed-verification-password"

    for _ in range(2):
        call_command(
            "seed_demo_user",
            email=email,
            username="seed-verifier",
            password=password,
            verbosity=0,
        )
        call_command("seed_demo_context", email=email, verbosity=0)

    user = get_user_model().objects.get(email=email)

    assert user.is_active
    assert user.check_password(password)
    assert Tenant.objects.filter(name="演示个人卖家空间").count() == 1
    assert TenantMembership.objects.filter(
        user=user,
        tenant__name="演示个人卖家空间",
    ).count() == 1
    assert AmazonStore.objects.filter(external_store_id="DEMO-STORE-US").count() == 1
    assert AdvertisingProfile.objects.filter(
        external_profile_id="DEMO-PROFILE-US-001"
    ).count() == 1
    assert Permission.objects.get(code="reports.upload").description
