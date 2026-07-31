import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework_simplejwt.exceptions import (
    TokenBackendError,
    TokenBackendExpiredToken,
)
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import (
    AuthenticationAuditEvent,
    ExternalIdentity,
    ExternalIdentitySource,
    RefreshTokenRecord,
)
from apps.core.errors import ErrorCode
from integrations.identity.scm import (
    RemoteIdentityProviderUnavailable,
    SCMIdentity,
    SCMIdentityProvider,
)

_DUMMY_PASSWORD_HASH = make_password("phase-2a-constant-time-placeholder")


@dataclass(frozen=True, slots=True)
class AuthServiceFailure(Exception):
    code: str
    message: str
    status_code: int = 401


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str


def normalize_identifier(identifier: str) -> str:
    return identifier.strip()


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _client_ip(request) -> str | None:
    return request.META.get("REMOTE_ADDR")


def _audit(
    request,
    *,
    event: str,
    outcome: str,
    user=None,
    identifier: str = "",
) -> None:
    AuthenticationAuditEvent.objects.create(
        event=event,
        outcome=outcome,
        user=user,
        email_hash=(
            _hash_value(normalize_identifier(identifier))
            if identifier
            else ""
        ),
        request_id=request.request_id,
        ip_address=_client_ip(request),
    )


def serialize_user(user) -> dict[str, str]:
    return {
        "id": str(user.pk),
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


def _refresh_expiry(token: RefreshToken) -> datetime:
    return datetime.fromtimestamp(int(token["exp"]), tz=UTC)


def _store_refresh_token(user, raw_token: str, token: RefreshToken) -> RefreshTokenRecord:
    return RefreshTokenRecord.objects.create(
        token_hash=_hash_value(raw_token),
        user=user,
        expires_at=_refresh_expiry(token),
    )


def _issue_tokens(user) -> IssuedTokens:
    refresh = RefreshToken.for_user(user)
    refresh["user_id"] = str(user.pk)
    raw_refresh = str(refresh)
    _store_refresh_token(user, raw_refresh, refresh)

    access = refresh.access_token
    access["user_id"] = str(user.pk)
    return IssuedTokens(
        access_token=str(access),
        refresh_token=raw_refresh,
    )


def _matching_local_user(identifier: str):
    user_model = get_user_model()
    matching_users = list(
        user_model.objects.filter(
            Q(username=identifier) | Q(email__iexact=identifier)
        ).order_by("pk")[:2]
    )
    return matching_users[0] if len(matching_users) == 1 else None


def _invalid_credentials(request, *, identifier: str, user=None):
    check_password("", _DUMMY_PASSWORD_HASH)
    _audit(
        request,
        event="login",
        outcome="invalid_credentials",
        user=user,
        identifier=identifier,
    )
    raise AuthServiceFailure(
        ErrorCode.AUTH_INVALID_CREDENTIALS,
        "账号或密码错误",
    )


def _external_email(identity: SCMIdentity) -> str:
    return f"scm-{identity.external_user_id}@external.invalid"


def _provision_external_identity_once(identity: SCMIdentity):
    source = ExternalIdentitySource.SCM_MERCHANT_ADMIN
    now = timezone.now()
    with transaction.atomic():
        mapping = (
            ExternalIdentity.objects.select_for_update()
            .select_related("user")
            .filter(
                source=source,
                external_user_id=identity.external_user_id,
            )
            .first()
        )
        if mapping is not None:
            identifier_conflict = (
                ExternalIdentity.objects.filter(
                    source=source,
                    identifier=identity.identifier,
                )
                .exclude(pk=mapping.pk)
                .exists()
            )
            if identifier_conflict:
                return None
            mapping.identifier = identity.identifier
            mapping.external_merchant_id = identity.merchant_id
            mapping.last_authenticated_at = now
            mapping.save(
                update_fields=[
                    "identifier",
                    "external_merchant_id",
                    "last_authenticated_at",
                    "updated_at",
                ]
            )
            return mapping.user

        if ExternalIdentity.objects.filter(
            source=source,
            identifier=identity.identifier,
        ).exists():
            return None

        user_model = get_user_model()
        if user_model.objects.filter(
            Q(username__iexact=identity.identifier)
            | Q(email__iexact=_external_email(identity))
        ).exists():
            return None

        user = user_model(
            username=identity.identifier,
            email=_external_email(identity),
        )
        user.set_unusable_password()
        user.save()
        ExternalIdentity.objects.create(
            user=user,
            source=source,
            external_user_id=identity.external_user_id,
            external_merchant_id=identity.merchant_id,
            identifier=identity.identifier,
            last_authenticated_at=now,
        )
        return user


def _provision_external_identity(identity: SCMIdentity):
    try:
        return _provision_external_identity_once(identity)
    except IntegrityError:
        mapping = (
            ExternalIdentity.objects.select_related("user")
            .filter(
                source=ExternalIdentitySource.SCM_MERCHANT_ADMIN,
                external_user_id=identity.external_user_id,
                identifier=identity.identifier,
            )
            .first()
        )
        return mapping.user if mapping is not None else None


def _authenticate_external(
    *,
    request,
    identifier: str,
    password: str,
):
    try:
        identity = SCMIdentityProvider().authenticate(
            identifier=identifier,
            password=password,
        )
    except RemoteIdentityProviderUnavailable as exc:
        _audit(
            request,
            event="login",
            outcome="provider_unavailable",
            identifier=identifier,
        )
        raise AuthServiceFailure(
            ErrorCode.SERVICE_NOT_READY,
            "远程账号服务暂不可用",
            503,
        ) from exc

    if identity is None:
        _invalid_credentials(request, identifier=identifier)
    if not identity.is_active:
        mapping = ExternalIdentity.objects.select_related("user").filter(
            source=ExternalIdentitySource.SCM_MERCHANT_ADMIN,
            external_user_id=identity.external_user_id,
        ).first()
        _audit(
            request,
            event="login",
            outcome="user_disabled",
            user=mapping.user if mapping is not None else None,
            identifier=identifier,
        )
        raise AuthServiceFailure(
            ErrorCode.AUTH_USER_DISABLED,
            "账号已停用",
        )

    user = _provision_external_identity(identity)
    if user is None:
        _invalid_credentials(request, identifier=identifier)
    if not user.is_active:
        _audit(
            request,
            event="login",
            outcome="user_disabled",
            user=user,
            identifier=identifier,
        )
        raise AuthServiceFailure(
            ErrorCode.AUTH_USER_DISABLED,
            "账号已停用",
        )
    return user


def login(
    *,
    request,
    identifier: str,
    password: str,
) -> tuple[IssuedTokens, object]:
    normalized_identifier = normalize_identifier(identifier)
    user = _matching_local_user(normalized_identifier)
    external_mapping = (
        ExternalIdentity.objects.filter(
            user=user,
            source=ExternalIdentitySource.SCM_MERCHANT_ADMIN,
        ).first()
        if user is not None
        else None
    )

    if external_mapping is not None or user is None:
        user = _authenticate_external(
            request=request,
            identifier=normalized_identifier,
            password=password,
        )
    elif not user.check_password(password):
        _invalid_credentials(
            request,
            identifier=normalized_identifier,
            user=user,
        )

    if not user.is_active:
        _audit(
            request,
            event="login",
            outcome="user_disabled",
            user=user,
            identifier=normalized_identifier,
        )
        raise AuthServiceFailure(
            ErrorCode.AUTH_USER_DISABLED,
            "账号已停用",
        )

    with transaction.atomic():
        issued = _issue_tokens(user)
        _audit(
            request,
            event="login",
            outcome="success",
            user=user,
            identifier=normalized_identifier,
        )
    return issued, user


def _decode_refresh(raw_token: str) -> dict:
    try:
        payload = token_backend.decode(raw_token, verify=True)
    except TokenBackendExpiredToken as exc:
        raise AuthServiceFailure(
            ErrorCode.AUTH_TOKEN_EXPIRED,
            "刷新令牌已过期",
        ) from exc
    except TokenBackendError as exc:
        raise AuthServiceFailure(
            ErrorCode.AUTH_TOKEN_INVALID,
            "刷新令牌无效",
        ) from exc

    if payload.get("token_type") != "refresh":
        raise AuthServiceFailure(
            ErrorCode.AUTH_TOKEN_INVALID,
            "刷新令牌类型无效",
        )
    return payload


def refresh(*, request, raw_token: str | None) -> tuple[str, str | None]:
    if not raw_token:
        _audit(request, event="refresh", outcome="token_missing")
        raise AuthServiceFailure(
            ErrorCode.AUTH_TOKEN_MISSING,
            "缺少刷新令牌",
        )

    try:
        payload = _decode_refresh(raw_token)
    except AuthServiceFailure as failure:
        _audit(
            request,
            event="refresh",
            outcome=(
                "token_expired"
                if failure.code == ErrorCode.AUTH_TOKEN_EXPIRED
                else "token_invalid"
            ),
        )
        raise

    failure: AuthServiceFailure | None = None
    failure_outcome = ""
    failure_user = None
    with transaction.atomic():
        record = (
            RefreshTokenRecord.objects.select_for_update()
            .select_related("user")
            .filter(token_hash=_hash_value(raw_token))
            .first()
        )
        if record is None:
            failure = AuthServiceFailure(
                ErrorCode.AUTH_TOKEN_REVOKED,
                "刷新令牌已撤销",
            )
            failure_outcome = "token_revoked"
        elif record.revoked_at is not None:
            failure = AuthServiceFailure(
                ErrorCode.AUTH_TOKEN_REVOKED,
                "刷新令牌已撤销",
            )
            failure_outcome = "token_revoked"
            failure_user = record.user
        elif record.expires_at <= timezone.now():
            failure = AuthServiceFailure(
                ErrorCode.AUTH_TOKEN_EXPIRED,
                "刷新令牌已过期",
            )
            failure_outcome = "token_expired"
            failure_user = record.user
        elif str(record.user_id) != str(payload.get("user_id")):
            failure = AuthServiceFailure(
                ErrorCode.AUTH_TOKEN_INVALID,
                "刷新令牌无效",
            )
            failure_outcome = "token_invalid"
        elif not record.user.is_active:
            failure = AuthServiceFailure(
                ErrorCode.AUTH_USER_DISABLED,
                "账号已停用",
            )
            failure_outcome = "user_disabled"
            failure_user = record.user
        else:
            replacement_refresh: str | None = None
            if settings.JWT_ROTATE_REFRESH_TOKENS:
                issued = _issue_tokens(record.user)
                replacement_refresh = issued.refresh_token
                if settings.JWT_BLACKLIST_AFTER_ROTATION:
                    record.revoked_at = timezone.now()
                    record.rotated_to = RefreshTokenRecord.objects.get(
                        token_hash=_hash_value(replacement_refresh)
                    )
                    record.save(update_fields=["revoked_at", "rotated_to"])
                access_token = issued.access_token
            else:
                access = AccessToken.for_user(record.user)
                access["user_id"] = str(record.user_id)
                access_token = str(access)

            _audit(
                request,
                event="refresh",
                outcome="success",
                user=record.user,
            )
            return access_token, replacement_refresh

    _audit(
        request,
        event="refresh",
        outcome=failure_outcome,
        user=failure_user,
    )
    raise failure


@transaction.atomic
def logout(*, request, raw_token: str | None) -> None:
    user = None
    if raw_token:
        try:
            payload = _decode_refresh(raw_token)
        except AuthServiceFailure:
            payload = None
        if payload is not None:
            record = (
                RefreshTokenRecord.objects.select_for_update()
                .select_related("user")
                .filter(token_hash=_hash_value(raw_token))
                .first()
            )
            if record is not None:
                user = record.user
                if record.revoked_at is None:
                    record.revoked_at = timezone.now()
                    record.save(update_fields=["revoked_at"])

    _audit(request, event="logout", outcome="success", user=user)
