import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.permissions.models import Permission
from apps.stores.models import (
    AdvertisingProfile,
    AmazonStore,
    Marketplace,
    StoreMarketplace,
)
from apps.tenants.models import MembershipRole, Tenant, TenantMembership, TenantType


PERMISSIONS = {
    "context.view": "查看卖家空间上下文",
    "reports.upload": "上传和重处理报表",
    "reports.view": "查看导入任务与错误",
    "advertising.view": "查看标准化广告主数据",
    "products.view": "查看产品与 Listing",
    "products.manage": "管理产品与 Listing",
    "analytics.view": "查看广告指标与异常",
    "analytics.configure": "配置目标 ACOS 与异常规则",
    "analysis.run": "运行智能分析",
    "recommendations.view": "查看优化建议",
    "actions.operate": "创建和提交 Action Preview",
    "approvals.approve": "审批优化方案",
    "executions.execute": "回填人工执行结果",
    "audit.view": "查看业务审计",
    "rbac.manage": "管理角色和授权",
    "knowledge.view": "查看知识中心",
}


class Command(BaseCommand):
    help = "Idempotently seed the fictional tenant/store/profile demo context."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default=os.environ.get("DEMO_USER_EMAIL", "demo@example.invalid"),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        email = user_model.objects.normalize_email(options["email"])
        user = user_model.objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            raise CommandError(
                "Create the demo account first with seed_demo_user; "
                f"active account not found: {email}"
            )

        for code, name in PERMISSIONS.items():
            Permission.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": name,
                },
            )

        tenant, _ = Tenant.objects.update_or_create(
            name="演示个人卖家空间",
            defaults={
                "tenant_type": TenantType.PERSONAL,
                "target_acos": "0.3000",
                "is_active": True,
            },
        )
        TenantMembership.objects.update_or_create(
            tenant=tenant,
            user=user,
            defaults={
                "membership_role": MembershipRole.OWNER,
                "is_active": True,
            },
        )

        marketplace, _ = Marketplace.objects.update_or_create(
            code="US",
            defaults={
                "name": "Amazon.com",
                "currency_code": "USD",
                "timezone": "America/Los_Angeles",
                "is_active": True,
            },
        )
        store, _ = AmazonStore.objects.update_or_create(
            tenant=tenant,
            external_store_id="DEMO-STORE-US",
            defaults={"name": "演示美国店", "is_active": True},
        )
        store_marketplace, _ = StoreMarketplace.objects.update_or_create(
            store=store,
            marketplace=marketplace,
            defaults={"is_active": True},
        )
        AdvertisingProfile.objects.update_or_create(
            store_marketplace=store_marketplace,
            external_profile_id="DEMO-PROFILE-US-001",
            defaults={
                "name": "演示 Sponsored Products Profile",
                "currency_code": "USD",
                "timezone": "America/Los_Angeles",
                "target_acos": "0.2800",
                "is_active": True,
            },
        )

        isolation_owner, _ = user_model.objects.get_or_create(
            email="isolation-owner@example.invalid",
            defaults={"username": "isolation-owner", "is_active": True},
        )
        if not isolation_owner.has_usable_password():
            isolation_owner.set_unusable_password()
            isolation_owner.save(update_fields=["password"])
        isolation_tenant, _ = Tenant.objects.update_or_create(
            name="隔离验证卖家空间",
            defaults={
                "tenant_type": TenantType.COMPANY,
                "is_active": True,
            },
        )
        TenantMembership.objects.update_or_create(
            tenant=isolation_tenant,
            user=isolation_owner,
            defaults={
                "membership_role": MembershipRole.OWNER,
                "is_active": True,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo context ready for {email}: tenant={tenant.pk}, "
                f"store={store.pk}, marketplace={marketplace.pk}"
            )
        )
