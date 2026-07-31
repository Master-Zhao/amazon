import logging
from dataclasses import dataclass

import bcrypt
from django.conf import settings
from django.db import DatabaseError, connections

logger = logging.getLogger(__name__)

SCM_ALIAS = "scm_remote"


class RemoteIdentityProviderUnavailable(Exception):
    pass


@dataclass(frozen=True, slots=True)
class SCMIdentity:
    external_user_id: str
    merchant_id: str
    identifier: str
    is_active: bool


class SCMIdentityProvider:
    def authenticate(
        self,
        *,
        identifier: str,
        password: str,
    ) -> SCMIdentity | None:
        if not settings.REMOTE_SCM_AUTH_ENABLED:
            return None
        if SCM_ALIAS not in settings.DATABASES:
            raise RemoteIdentityProviderUnavailable(
                "SCM identity database is not configured"
            )

        try:
            with connections[SCM_ALIAS].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        merchant_admin_id,
                        mer_id,
                        account,
                        pwd,
                        status,
                        is_del
                    FROM eb_merchant_admin
                    WHERE BINARY account = BINARY %s
                    ORDER BY merchant_admin_id
                    LIMIT 2
                    """,
                    [identifier],
                )
                rows = list(cursor.fetchall())
        except DatabaseError as exc:
            logger.exception(
                "Remote SCM identity query failed",
                extra={"identity_source": "SCM_MERCHANT_ADMIN"},
            )
            raise RemoteIdentityProviderUnavailable() from exc

        if len(rows) != 1:
            return None

        external_user_id, merchant_id, account, encoded, status, is_deleted = (
            rows[0]
        )
        try:
            password_matches = bcrypt.checkpw(
                password.encode("utf-8"),
                str(encoded).encode("ascii"),
            )
        except (TypeError, ValueError, UnicodeEncodeError):
            logger.warning(
                "Remote SCM identity has an unsupported password hash",
                extra={
                    "identity_source": "SCM_MERCHANT_ADMIN",
                    "external_user_id": str(external_user_id),
                },
            )
            return None
        if not password_matches:
            return None

        return SCMIdentity(
            external_user_id=str(external_user_id),
            merchant_id=str(merchant_id),
            identifier=str(account),
            is_active=int(status) == 1 and int(is_deleted) == 0,
        )
