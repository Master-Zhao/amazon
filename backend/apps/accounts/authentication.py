from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework_simplejwt.exceptions import (
    TokenBackendError,
    TokenBackendExpiredToken,
)
from rest_framework_simplejwt.state import token_backend

from apps.accounts.exceptions import AuthenticationAPIException
from apps.core.errors import ErrorCode


class AccessTokenAuthentication(BaseAuthentication):
    keyword = b"Bearer"

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != self.keyword.lower():
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_INVALID,
                "访问令牌格式无效",
            )

        try:
            raw_token = header[1].decode("ascii")
        except UnicodeDecodeError as exc:
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_INVALID,
                "访问令牌格式无效",
            ) from exc

        try:
            payload = token_backend.decode(raw_token, verify=True)
        except TokenBackendExpiredToken as exc:
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_EXPIRED,
                "访问令牌已过期",
            ) from exc
        except TokenBackendError as exc:
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_INVALID,
                "访问令牌无效",
            ) from exc

        if payload.get("token_type") != "access":
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_INVALID,
                "访问令牌类型无效",
            )

        user_id = payload.get("user_id")
        if user_id is None:
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_INVALID,
                "访问令牌缺少用户标识",
            )

        user_model = get_user_model()
        try:
            user = user_model.objects.get(pk=user_id)
        except (user_model.DoesNotExist, ValueError, TypeError) as exc:
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_INVALID,
                "访问令牌无效",
            ) from exc

        if not user.is_active:
            raise AuthenticationAPIException(
                ErrorCode.AUTH_USER_DISABLED,
                "账号已停用",
            )

        return user, payload

    def authenticate_header(self, request):
        return "Bearer"
