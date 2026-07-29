import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.permissions.models import (
    Permission,
    ProfileAccessLevel,
    Role,
    RolePermission,
    TeamProfileAccess,
    TeamStoreAccess,
    UserProfileAccess,
    UserRole,
    UserStoreAccess,
)
from apps.stores.models import (
    AdvertisingProfile,
    AmazonStore,
    Marketplace,
    StoreMarketplace,
)
from apps.tenants.models import (
    MembershipRole,
    Team,
    TeamMember,
    Tenant,
    TenantMembership,
    TenantType,
)


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

VIEW_ONLY_PERMS = [
    "context.view",
    "reports.view",
    "advertising.view",
    "products.view",
    "analytics.view",
    "recommendations.view",
    "audit.view",
    "knowledge.view",
]

OPERATOR_PERMS = VIEW_ONLY_PERMS + [
    "reports.upload",
    "products.manage",
    "analysis.run",
    "actions.operate",
    "executions.execute",
]

MANAGER_PERMS = OPERATOR_PERMS + [
    "analytics.configure",
    "approvals.approve",
    "rbac.manage",
]

ALL_PERMS = list(PERMISSIONS.keys())


class Command(BaseCommand):
    help = "Seed comprehensive demo accounts: company tenant, multi-store, and permission-differentiated users."

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        seed_password = os.environ.get("DEMO_SEED_PASSWORD")

        for code, name in PERMISSIONS.items():
            Permission.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": name},
            )
        self.stdout.write("Permissions seeded.")

        us, _ = Marketplace.objects.update_or_create(
            code="US",
            defaults={
                "name": "Amazon.com",
                "currency_code": "USD",
                "timezone": "America/Los_Angeles",
                "is_active": True,
            },
        )
        uk, _ = Marketplace.objects.update_or_create(
            code="UK",
            defaults={
                "name": "Amazon.co.uk",
                "currency_code": "GBP",
                "timezone": "Europe/London",
                "is_active": True,
            },
        )
        jp, _ = Marketplace.objects.update_or_create(
            code="JP",
            defaults={
                "name": "Amazon.co.jp",
                "currency_code": "JPY",
                "timezone": "Asia/Tokyo",
                "is_active": True,
            },
        )
        de, _ = Marketplace.objects.update_or_create(
            code="DE",
            defaults={
                "name": "Amazon.de",
                "currency_code": "EUR",
                "timezone": "Europe/Berlin",
                "is_active": True,
            },
        )
        self.stdout.write("Marketplaces seeded: US, UK, JP, DE.")

        company_owner = self._ensure_user(
            user_model,
            email="company-owner@example.invalid",
            username="company-owner",
            password=seed_password,
        )
        company_tenant = self._create_company_tenant(company_owner)
        self._create_company_stores_and_profiles(company_tenant, us, uk, jp, de)
        self._create_company_teams_and_roles(company_tenant, user_model, us, uk, jp, de)
        self.stdout.write(self.style.SUCCESS("Company tenant with teams and roles seeded."))

        multi_store_user = self._ensure_user(
            user_model,
            email="multi-store@example.invalid",
            username="multi-store-seller",
            password=seed_password,
        )
        self._create_multi_store_personal(multi_store_user, us, uk, jp)
        self.stdout.write(self.style.SUCCESS("Multi-store personal tenant seeded."))

        viewer_user = self._ensure_user(
            user_model,
            email="viewer@example.invalid",
            username="viewer",
            password=seed_password,
        )
        self._create_viewer_account(viewer_user, company_tenant, us, uk)
        self.stdout.write(self.style.SUCCESS("Viewer-only account seeded."))

        operator_user = self._ensure_user(
            user_model,
            email="operator@example.invalid",
            username="operator",
            password=seed_password,
        )
        self._create_operator_account(operator_user, company_tenant, us, uk)
        self.stdout.write(self.style.SUCCESS("Operator account seeded."))

        manager_user = self._ensure_user(
            user_model,
            email="manager@example.invalid",
            username="manager",
            password=seed_password,
        )
        self._create_manager_account(manager_user, company_tenant, us, uk)
        self.stdout.write(self.style.SUCCESS("Manager account seeded."))

        self._print_summary()

    def _ensure_user(self, user_model, *, email, username, password):
        email = user_model.objects.normalize_email(email)
        user, created = user_model.objects.get_or_create(
            email=email,
            defaults={"username": username, "is_active": True},
        )
        if password:
            user.set_password(password)
        elif created:
            user.set_unusable_password()
        user.username = username
        user.is_active = True
        user.save()
        tag = "created" if created else "updated"
        self.stdout.write(f"  User {tag}: {email}")
        return user

    def _create_company_tenant(self, owner):
        tenant, _ = Tenant.objects.update_or_create(
            name="星辰广告公司",
            defaults={
                "tenant_type": TenantType.COMPANY,
                "target_acos": "0.2500",
                "is_active": True,
            },
        )
        TenantMembership.objects.update_or_create(
            tenant=tenant,
            user=owner,
            defaults={
                "membership_role": MembershipRole.OWNER,
                "is_active": True,
            },
        )
        return tenant

    def _create_company_stores_and_profiles(self, tenant, us, uk, jp, de):
        stores_data = [
            ("COMPANY-STORE-US", "星辰美国站", us, "USD", "America/Los_Angeles", "0.2500"),
            ("COMPANY-STORE-UK", "星辰英国站", uk, "GBP", "Europe/London", "0.2800"),
            ("COMPANY-STORE-JP", "星辰日本站", jp, "JPY", "Asia/Tokyo", "0.2200"),
            ("COMPANY-STORE-DE", "星辰德国站", de, "EUR", "Europe/Berlin", "0.3000"),
        ]
        for ext_id, name, marketplace, currency, tz, acos in stores_data:
            store, _ = AmazonStore.objects.update_or_create(
                tenant=tenant,
                external_store_id=ext_id,
                defaults={"name": name, "is_active": True},
            )
            sm, _ = StoreMarketplace.objects.update_or_create(
                store=store,
                marketplace=marketplace,
                defaults={"is_active": True},
            )
            AdvertisingProfile.objects.update_or_create(
                store_marketplace=sm,
                external_profile_id=f"{ext_id}-SP-001",
                defaults={
                    "name": f"{name} SP Profile",
                    "currency_code": currency,
                    "timezone": tz,
                    "target_acos": acos,
                    "is_active": True,
                },
            )

    def _create_company_teams_and_roles(self, tenant, user_model, us, uk, jp, de):
        admin_role = self._ensure_role(tenant, "公司管理员", "company-admin", ALL_PERMS)
        ops_role = self._ensure_role(tenant, "运营专员", "company-operator", OPERATOR_PERMS)
        viewer_role = self._ensure_role(tenant, "只读观察员", "company-viewer", VIEW_ONLY_PERMS)

        owner_membership = TenantMembership.objects.get(
            tenant=tenant, user__email="company-owner@example.invalid"
        )
        UserRole.objects.update_or_create(
            membership=owner_membership,
            role=admin_role,
            defaults={},
        )

        ops_team, _ = Team.objects.update_or_create(
            tenant=tenant,
            name="运营团队",
            defaults={"is_active": True},
        )
        analytics_team, _ = Team.objects.update_or_create(
            tenant=tenant,
            name="分析团队",
            defaults={"is_active": True},
        )

        us_store = AmazonStore.objects.get(tenant=tenant, external_store_id="COMPANY-STORE-US")
        uk_store = AmazonStore.objects.get(tenant=tenant, external_store_id="COMPANY-STORE-UK")
        jp_store = AmazonStore.objects.get(tenant=tenant, external_store_id="COMPANY-STORE-JP")
        de_store = AmazonStore.objects.get(tenant=tenant, external_store_id="COMPANY-STORE-DE")

        for store in [us_store, uk_store, jp_store, de_store]:
            TeamStoreAccess.objects.update_or_create(
                team=ops_team, store=store, defaults={}
            )
        for store in [us_store, uk_store]:
            TeamStoreAccess.objects.update_or_create(
                team=analytics_team, store=store, defaults={}
            )

        all_profiles = []
        for store in [us_store, uk_store, jp_store, de_store]:
            all_profiles.extend(AdvertisingProfile.objects.filter(store_marketplace__store=store))

        for profile in all_profiles:
            TeamProfileAccess.objects.update_or_create(
                team=ops_team,
                profile=profile,
                defaults={"access_level": ProfileAccessLevel.OPERATE},
            )
        for profile in all_profiles:
            if profile.store_marketplace.store_id in [us_store.pk, uk_store.pk]:
                TeamProfileAccess.objects.update_or_create(
                    team=analytics_team,
                    profile=profile,
                    defaults={"access_level": ProfileAccessLevel.VIEW},
                )

    def _create_multi_store_personal(self, user, us, uk, jp):
        tenant, _ = Tenant.objects.update_or_create(
            name="多店铺个人卖家",
            defaults={
                "tenant_type": TenantType.PERSONAL,
                "target_acos": "0.3000",
                "is_active": True,
            },
        )
        membership, _ = TenantMembership.objects.update_or_create(
            tenant=tenant,
            user=user,
            defaults={
                "membership_role": MembershipRole.OWNER,
                "is_active": True,
            },
        )

        stores_data = [
            ("MULTI-STORE-US", "我的美国店", us, "USD", "America/Los_Angeles", "0.2800"),
            ("MULTI-STORE-UK", "我的英国店", uk, "GBP", "Europe/London", "0.3200"),
            ("MULTI-STORE-JP", "我的日本店", jp, "JPY", "Asia/Tokyo", "0.2500"),
        ]
        for ext_id, name, marketplace, currency, tz, acos in stores_data:
            store, _ = AmazonStore.objects.update_or_create(
                tenant=tenant,
                external_store_id=ext_id,
                defaults={"name": name, "is_active": True},
            )
            sm, _ = StoreMarketplace.objects.update_or_create(
                store=store,
                marketplace=marketplace,
                defaults={"is_active": True},
            )
            profile, _ = AdvertisingProfile.objects.update_or_create(
                store_marketplace=sm,
                external_profile_id=f"{ext_id}-SP-001",
                defaults={
                    "name": f"{name} SP Profile",
                    "currency_code": currency,
                    "timezone": tz,
                    "target_acos": acos,
                    "is_active": True,
                },
            )
            UserStoreAccess.objects.update_or_create(
                user=user, store=store, defaults={}
            )
            UserProfileAccess.objects.update_or_create(
                user=user,
                profile=profile,
                defaults={"access_level": ProfileAccessLevel.MANAGE},
            )

        full_role = self._ensure_role(tenant, "个人全权", "personal-full", ALL_PERMS)
        UserRole.objects.update_or_create(
            membership=membership, role=full_role, defaults={}
        )

    def _create_viewer_account(self, user, company_tenant, us, uk):
        membership, _ = TenantMembership.objects.update_or_create(
            tenant=company_tenant,
            user=user,
            defaults={
                "membership_role": MembershipRole.MEMBER,
                "is_active": True,
            },
        )
        viewer_role = self._ensure_role(
            company_tenant, "公司只读观察员", "company-viewer", VIEW_ONLY_PERMS
        )
        UserRole.objects.update_or_create(
            membership=membership, role=viewer_role, defaults={}
        )

        us_store = AmazonStore.objects.get(
            tenant=company_tenant, external_store_id="COMPANY-STORE-US"
        )
        uk_store = AmazonStore.objects.get(
            tenant=company_tenant, external_store_id="COMPANY-STORE-UK"
        )
        for store in [us_store, uk_store]:
            UserStoreAccess.objects.update_or_create(
                user=user, store=store, defaults={}
            )
        for store in [us_store, uk_store]:
            for profile in AdvertisingProfile.objects.filter(store_marketplace__store=store):
                UserProfileAccess.objects.update_or_create(
                    user=user,
                    profile=profile,
                    defaults={"access_level": ProfileAccessLevel.VIEW},
                )

    def _create_operator_account(self, user, company_tenant, us, uk):
        membership, _ = TenantMembership.objects.update_or_create(
            tenant=company_tenant,
            user=user,
            defaults={
                "membership_role": MembershipRole.MEMBER,
                "is_active": True,
            },
        )
        ops_role = self._ensure_role(
            company_tenant, "公司运营专员", "company-operator", OPERATOR_PERMS
        )
        UserRole.objects.update_or_create(
            membership=membership, role=ops_role, defaults={}
        )

        us_store = AmazonStore.objects.get(
            tenant=company_tenant, external_store_id="COMPANY-STORE-US"
        )
        uk_store = AmazonStore.objects.get(
            tenant=company_tenant, external_store_id="COMPANY-STORE-UK"
        )
        jp_store = AmazonStore.objects.get(
            tenant=company_tenant, external_store_id="COMPANY-STORE-JP"
        )
        for store in [us_store, uk_store, jp_store]:
            UserStoreAccess.objects.update_or_create(
                user=user, store=store, defaults={}
            )
        for store in [us_store, uk_store, jp_store]:
            for profile in AdvertisingProfile.objects.filter(store_marketplace__store=store):
                UserProfileAccess.objects.update_or_create(
                    user=user,
                    profile=profile,
                    defaults={"access_level": ProfileAccessLevel.OPERATE},
                )

        ops_team = Team.objects.get(tenant=company_tenant, name="运营团队")
        TeamMember.objects.update_or_create(
            team=ops_team, membership=membership, defaults={}
        )

    def _create_manager_account(self, user, company_tenant, us, uk):
        membership, _ = TenantMembership.objects.update_or_create(
            tenant=company_tenant,
            user=user,
            defaults={
                "membership_role": MembershipRole.ADMIN,
                "is_active": True,
            },
        )
        manager_role = self._ensure_role(
            company_tenant, "公司管理员", "company-admin", MANAGER_PERMS
        )
        UserRole.objects.update_or_create(
            membership=membership, role=manager_role, defaults={}
        )

        for store in AmazonStore.objects.filter(tenant=company_tenant):
            UserStoreAccess.objects.update_or_create(
                user=user, store=store, defaults={}
            )
        for profile in AdvertisingProfile.objects.filter(
            store_marketplace__store__tenant=company_tenant
        ):
            UserProfileAccess.objects.update_or_create(
                user=user,
                profile=profile,
                defaults={"access_level": ProfileAccessLevel.APPROVE},
            )

    def _ensure_role(self, tenant, name, code, perm_codes):
        role, _ = Role.objects.update_or_create(
            code=code,
            defaults={
                "tenant": tenant,
                "name": name,
                "is_system": False,
                "is_active": True,
            },
        )
        for perm_code in perm_codes:
            perm = Permission.objects.get(code=perm_code)
            RolePermission.objects.update_or_create(
                role=role, permission=perm, defaults={}
            )
        return role

    def _print_summary(self):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("  种子数据创建完成 - 账户一览"))
        self.stdout.write("=" * 60)

        accounts = [
            ("demo@example.invalid", "演示个人卖家（已有）", "PERSONAL / OWNER / 全部权限"),
            ("company-owner@example.invalid", "星辰广告公司老板", "COMPANY / OWNER / 4店4站 / 全部权限"),
            ("multi-store@example.invalid", "多店铺个人卖家", "PERSONAL / OWNER / 3店3站 / 全部权限"),
            ("manager@example.invalid", "公司管理员", "COMPANY / ADMIN / 4店4站 / 管理级权限"),
            ("operator@example.invalid", "运营专员", "COMPANY / MEMBER / 3店 / 运营级权限 + 运营团队"),
            ("viewer@example.invalid", "只读观察员", "COMPANY / MEMBER / 2店 / 只读权限"),
        ]
        for email, desc, detail in accounts:
            self.stdout.write(f"\n  {desc}")
            self.stdout.write(f"    邮箱: {email}")
            self.stdout.write(f"    配置: {detail}")
        self.stdout.write(
            "\n  登录密码不写入代码或输出；如需为本命令创建的新账号启用登录，"
            "请在运行前设置 DEMO_SEED_PASSWORD。"
        )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  权限等级说明")
        self.stdout.write("=" * 60)
        self.stdout.write("  只读观察员: 查看数据，不可操作")
        self.stdout.write("  运营专员:   查看 + 上传/分析/操作/执行")
        self.stdout.write("  管理员:     运营 + 配置/审批/授权")
        self.stdout.write("  Owner:      全部权限")
        self.stdout.write("")
        self.stdout.write("  Profile 访问级别: VIEW(10) < OPERATE(20) < APPROVE(30) < EXECUTE(40) < MANAGE(50)")
        self.stdout.write("=" * 60)
