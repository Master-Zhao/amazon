import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.exceptions import (
    TokenBackendError,
    TokenBackendExpiredToken,
)
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import AuthenticationAuditEvent, RefreshTokenRecord
from apps.core.errors import ErrorCode

_DUMMY_PASSWORD_HASH = make_password("phase-2a-constant-time-placeholder")


@dataclass(frozen=True, slots=True)
class AuthServiceFailure(Exception):
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str


def normalize_email(email: str) -> str:
    user_model = get_user_model()
    return user_model.objects.normalize_email(email)


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
    email: str = "",
) -> None:
    AuthenticationAuditEvent.objects.create(
        event=event,
        outcome=outcome,
        user=user,
        email_hash=_hash_value(normalize_email(email)) if email else "",
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


def login(*, request, email: str, password: str) -> tuple[IssuedTokens, object]:
    normalized_email = normalize_email(email)
    user_model = get_user_model()
    user = user_model.objects.filter(email__iexact=normalized_email).first()

    if user is None:
        check_password(password, _DUMMY_PASSWORD_HASH)
        _audit(
            request,
            event="login",
            outcome="invalid_credentials",
            email=normalized_email,
        )
        raise AuthServiceFailure(
            ErrorCode.AUTH_INVALID_CREDENTIALS,
            "邮箱或密码错误",
        )

    if not user.check_password(password):
        _audit(
            request,
            event="login",
            outcome="invalid_credentials",
            user=user,
            email=normalized_email,
        )
        raise AuthServiceFailure(
            ErrorCode.AUTH_INVALID_CREDENTIALS,
            "邮箱或密码错误",
        )

    if not user.is_active:
        _audit(
            request,
            event="login",
            outcome="user_disabled",
            user=user,
            email=normalized_email,
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
            email=normalized_email,
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
