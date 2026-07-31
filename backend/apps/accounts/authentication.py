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

    def _authorization_token(self, request) -> str | None:
        header = get_authorization_header(request).split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != self.keyword.lower():
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_INVALID,
                "访问令牌格式无效",
            )

        try:
            return header[1].decode("ascii")
        except UnicodeDecodeError as exc:
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_INVALID,
                "访问令牌格式无效",
            ) from exc

    def _x_token(self, request) -> str | None:
        value = request.META.get("HTTP_X_TOKEN")
        if value is None:
            return None
        raw_token = str(value).strip()
        if not raw_token or any(character.isspace() for character in raw_token):
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_INVALID,
                "访问令牌格式无效",
            )
        return raw_token

    def authenticate(self, request):
        authorization_token = self._authorization_token(request)
        x_token = self._x_token(request)
        if authorization_token is None and x_token is None:
            return None
        if (
            authorization_token is not None
            and x_token is not None
            and authorization_token != x_token
        ):
            raise AuthenticationAPIException(
                ErrorCode.AUTH_TOKEN_INVALID,
                "认证标头中的访问令牌不一致",
            )
        raw_token = authorization_token or x_token

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
