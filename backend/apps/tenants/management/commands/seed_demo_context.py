import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.permissions.models import (
    Permission,
    Role,
    RolePermission,
)
from apps.permissions.services import PERMISSION_CATALOG, seed_permission_catalog
from apps.stores.models import (
    AdvertisingProfile,
    AmazonStore,
    Marketplace,
    StoreMarketplace,
)
from apps.tenants.models import MembershipRole, Tenant, TenantMembership, TenantType


class Command(BaseCommand):
    help = "创建虚构演示 Tenant、Store、Marketplace、Profile 与权限上下文"

    def add_arguments(self, parser):
        parser.add_argument("--email", default="owner@example.invalid")
        parser.add_argument("--password", default=None)

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"] or os.environ.get("DEMO_USER_PASSWORD")
        if not password:
            raise CommandError("必须通过 --password 或 DEMO_USER_PASSWORD 提供演示密码")
        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(
            email=user_model.objects.normalize_email(options["email"]),
            defaults={"username": "demo-owner"},
        )
        user.set_password(password)
        user.is_active = True
        user.save()

        seed_permission_catalog()
        tenant, _ = Tenant.objects.get_or_create(
            name="虚构演示卖家空间",
            defaults={"tenant_type": TenantType.PERSONAL, "target_acos": "0.2500"},
        )
        TenantMembership.objects.update_or_create(
            tenant=tenant,
            user=user,
            defaults={"role": MembershipRole.OWNER, "is_active": True},
        )
        role, _ = Role.objects.get_or_create(
            tenant=None,
            code="system_owner",
            defaults={"name": "系统所有者", "is_system": True},
        )
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission=permission)
                for permission in Permission.objects.all()
            ],
            ignore_conflicts=True,
        )
        marketplace, _ = Marketplace.objects.get_or_create(
            code="US",
            defaults={
                "name": "Amazon.com",
                "country_code": "US",
                "currency": "USD",
                "timezone": "America/Los_Angeles",
            },
        )
        store, _ = AmazonStore.objects.get_or_create(
            tenant=tenant,
            external_store_id="DEMO-STORE-001",
            defaults={"name": "演示美国店"},
        )
        scope, _ = StoreMarketplace.objects.get_or_create(
            store=store,
            marketplace=marketplace,
            defaults={"seller_id": "DEMO-SELLER-001"},
        )
        profile, _ = AdvertisingProfile.objects.get_or_create(
            store_marketplace=scope,
            external_profile_id="DEMO-PROFILE-001",
            defaults={
                "name": "演示广告账户",
                "currency": "USD",
                "timezone": marketplace.timezone,
                "target_acos": "0.2200",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"演示上下文就绪: tenant={tenant.pk} store={store.pk} profile={profile.pk}"
            )
        )
