import hashlib


def tenant_cache_key(
    *,
    tenant_id,
    namespace: str,
    profile_id=None,
    parts: tuple[object, ...] = (),
) -> str:
    """Build a non-secret cache key that cannot collide across tenant/profile scope."""

    if not tenant_id or not namespace or ":" in namespace:
        raise ValueError("tenant_id and a colon-free namespace are required")
    scope = [f"tenant={tenant_id}", f"profile={profile_id or '-'}"]
    digest = hashlib.sha256(
        "\x1f".join(str(part) for part in parts).encode("utf-8")
    ).hexdigest()[:24]
    return f"{namespace}:{':'.join(scope)}:{digest}"
