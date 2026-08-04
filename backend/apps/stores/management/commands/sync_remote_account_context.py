from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction

from apps.accounts.models import ExternalIdentitySource
from apps.stores.models import (
    AdvertisingProfile,
    AdvertisingProfileRemoteScope,
    AmazonStore,
    Marketplace,
    StoreMarketplace,
)
from apps.tenants.models import MembershipRole, Tenant, TenantMembership, TenantType
from integrations.advertising_data.remote_databases import ANALYSIS_ALIAS


class Command(BaseCommand):
    help = (
        "Create or update a local Tenant/Store/Profile context for one authenticated "
        "SCM account after verifying its remote Campaign scope."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--merchant-code")
        parser.add_argument("--marketplace-code", default="US")
        parser.add_argument("--marketplace-name", default="Amazon.com")
        parser.add_argument("--currency-code", default="USD")
        parser.add_argument("--timezone", default="America/Los_Angeles")

    def handle(self, *args, **options):
        user = (
            get_user_model()
            .objects.filter(username__iexact=options["username"], is_active=True)
            .first()
        )
        if user is None:
            raise CommandError("Active account not found.")
        identity = user.external_identities.filter(
            source=ExternalIdentitySource.SCM_MERCHANT_ADMIN
        ).first()
        if identity is None:
            raise CommandError("The account has no authenticated SCM identity.")
        try:
            merchant_id = int(identity.external_merchant_id)
        except ValueError as exc:
            raise CommandError("SCM merchant id must be numeric.") from exc

        with connections[ANALYSIS_ALIAS].cursor() as cursor:
            cursor.execute(
                """
                SELECT mer_code, COUNT(*), MAX(DATE(creation_date))
                FROM bi_analyze_ad_campaign
                WHERE mer_id = %s
                  AND mer_code IS NOT NULL
                  AND TRIM(mer_code) <> ''
                GROUP BY mer_code
                ORDER BY mer_code
                """,
                [merchant_id],
            )
            scopes = [(str(code), int(count), latest) for code, count, latest in cursor.fetchall()]
        requested_code = (options.get("merchant_code") or "").strip()
        if requested_code:
            matches = [scope for scope in scopes if scope[0] == requested_code]
        else:
            matches = scopes
        if len(matches) != 1:
            available = ", ".join(scope[0] for scope in scopes) or "none"
            raise CommandError(
                "Expected exactly one remote merchant code; "
                f"available codes: {available}. Use --merchant-code explicitly."
            )
        merchant_code, row_count, latest = matches[0]
        marketplace_code = options["marketplace_code"].upper()
        currency_code = options["currency_code"].upper()

        with transaction.atomic():
            tenant, _ = Tenant.objects.update_or_create(
                name=f"{user.username} 个人卖家空间",
                defaults={"tenant_type": TenantType.PERSONAL, "is_active": True},
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
                code=marketplace_code,
                defaults={
                    "name": options["marketplace_name"],
                    "currency_code": currency_code,
                    "timezone": options["timezone"],
                    "is_active": True,
                },
            )
            store, _ = AmazonStore.objects.update_or_create(
                tenant=tenant,
                external_store_id=f"SCM-MERCHANT-{merchant_id}",
                defaults={
                    "name": f"{user.username} 广告店铺",
                    "is_active": True,
                },
            )
            store_marketplace, _ = StoreMarketplace.objects.update_or_create(
                store=store,
                marketplace=marketplace,
                defaults={"is_active": True},
            )
            profile, _ = AdvertisingProfile.objects.update_or_create(
                store_marketplace=store_marketplace,
                external_profile_id=f"SCM-{merchant_id}-{merchant_code}",
                defaults={
                    "name": f"{merchant_code} Sponsored Products",
                    "currency_code": currency_code,
                    "timezone": options["timezone"],
                    "is_active": True,
                },
            )
            AdvertisingProfileRemoteScope.objects.update_or_create(
                profile=profile,
                defaults={
                    "external_merchant_id": identity.external_merchant_id,
                    "merchant_code": merchant_code,
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Remote context ready: "
                f"tenant={tenant.pk}, store={store.pk}, profile={profile.pk}, "
                f"rows={row_count}, dataThrough={latest}"
            )
        )
