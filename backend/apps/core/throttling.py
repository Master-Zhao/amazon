from rest_framework.throttling import SimpleRateThrottle


class TenantUserRateThrottle(SimpleRateThrottle):
    """Rate-limit authenticated callers without sharing counters across tenants."""

    scope = "tenant_user"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        tenant_id = request.headers.get("X-Tenant-ID") or "no-tenant"
        ident = f"user:{request.user.pk}:tenant:{tenant_id}"
        return self.cache_format % {"scope": self.scope, "ident": ident}
