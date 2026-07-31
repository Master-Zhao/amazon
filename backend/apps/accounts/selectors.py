from rest_framework.exceptions import NotFound

from apps.accounts.exceptions import AuthenticationAPIException
from apps.accounts.models import ExternalIdentity, ExternalIdentitySource
from apps.core.errors import ErrorCode
from integrations.identity.scm import (
    RemoteIdentityProviderUnavailable,
    SCMIdentityProvider,
)


def remote_account_for_user(user) -> dict[str, str | bool]:
    mapping = (
        ExternalIdentity.objects.filter(
            user=user,
            source=ExternalIdentitySource.SCM_MERCHANT_ADMIN,
        )
        .order_by("pk")
        .first()
    )
    if mapping is None:
        raise NotFound("当前账号没有远程 SCM 身份映射")

    try:
        snapshot = SCMIdentityProvider().account_snapshot(
            external_user_id=mapping.external_user_id,
            merchant_id=mapping.external_merchant_id,
            identifier=mapping.identifier,
        )
    except RemoteIdentityProviderUnavailable as exc:
        raise AuthenticationAPIException(
            ErrorCode.SERVICE_NOT_READY,
            "远程 SCM 数据服务暂不可用",
            status_code=503,
        ) from exc

    if snapshot is None:
        raise NotFound("远程 SCM 账号不存在或身份映射已失效")

    return {
        "source": ExternalIdentitySource.SCM_MERCHANT_ADMIN,
        "external_user_id": snapshot.external_user_id,
        "merchant_id": snapshot.merchant_id,
        "identifier": snapshot.identifier,
        "is_active": snapshot.is_active,
    }
