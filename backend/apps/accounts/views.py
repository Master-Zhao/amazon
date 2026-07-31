from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.exceptions import AuthenticationAPIException
from apps.accounts.serializers import (
    AccessTokenResponseSerializer,
    CurrentUserResponseSerializer,
    EmptyResponseSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    RemoteAccountResponseSerializer,
)
from apps.accounts.selectors import remote_account_for_user
from apps.accounts.services import (
    AuthServiceFailure,
    login,
    logout,
    refresh,
    serialize_user,
)
from apps.core.responses import api_response


def _set_refresh_cookie(response, token: str) -> None:
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        token,
        max_age=settings.JWT_REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        secure=settings.JWT_COOKIE_SECURE,
        httponly=settings.JWT_COOKIE_HTTP_ONLY,
        samesite=settings.JWT_COOKIE_SAME_SITE,
    )


def _clear_refresh_cookie(response) -> None:
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        "",
        max_age=0,
        expires="Thu, 01 Jan 1970 00:00:00 GMT",
        path=settings.JWT_REFRESH_COOKIE_PATH,
        secure=settings.JWT_COOKIE_SECURE,
        httponly=settings.JWT_COOKIE_HTTP_ONLY,
        samesite=settings.JWT_COOKIE_SAME_SITE,
    )


def _raise_api_failure(failure: AuthServiceFailure) -> None:
    raise AuthenticationAPIException(
        failure.code,
        failure.message,
        status_code=failure.status_code,
    )


class LoginView(APIView):
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    @extend_schema(
        summary="使用账号或邮箱和密码登录",
        description=(
            "推荐使用 identifier 提交用户名、账号编号或邮箱；兼容旧 email "
            "字段，但两者不能同时提供。响应体返回短期 Access Token 和基本"
            "用户信息；长期 Refresh Token 仅通过受环境配置约束的 HttpOnly "
            "Cookie 设置，不出现在 JSON 中。"
        ),
        request=LoginSerializer,
        responses={200: LoginResponseSerializer},
        tags=["authentication"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            issued, user = login(request=request, **serializer.validated_data)
        except AuthServiceFailure as failure:
            _raise_api_failure(failure)

        response = api_response(
            request,
            data={
                "access_token": issued.access_token,
                "user": serialize_user(user),
            },
            message="登录成功",
        )
        _set_refresh_cookie(response, issued.refresh_token)
        return response


class RefreshView(APIView):
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    @extend_schema(
        summary="使用 HttpOnly Cookie 刷新访问令牌",
        description=(
            "从 Refresh Cookie 读取令牌，返回新的 Access Token。按配置轮换 "
            "Refresh Cookie 并撤销旧刷新会话。"
        ),
        request=None,
        responses={
            200: AccessTokenResponseSerializer,
            401: OpenApiResponse(description="刷新令牌缺失、无效、过期或已撤销"),
        },
        tags=["authentication"],
    )
    def post(self, request):
        raw_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        try:
            access_token, replacement_refresh = refresh(
                request=request,
                raw_token=raw_token,
            )
        except AuthServiceFailure as failure:
            _raise_api_failure(failure)

        response = api_response(
            request,
            data={"access_token": access_token},
            message="访问令牌已刷新",
        )
        if replacement_refresh is not None:
            _set_refresh_cookie(response, replacement_refresh)
        return response


class LogoutView(APIView):
    authentication_classes: list[type] = []
    permission_classes: list[type] = []

    @extend_schema(
        summary="撤销当前刷新令牌并清除 Cookie",
        description="操作幂等；始终以原 Path、Secure、HttpOnly 和 SameSite 属性清除 Cookie。",
        request=None,
        responses={200: EmptyResponseSerializer},
        tags=["authentication"],
    )
    def post(self, request):
        logout(
            request=request,
            raw_token=request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME),
        )
        response = api_response(
            request,
            data={},
            message="已退出登录",
            status=status.HTTP_200_OK,
        )
        _clear_refresh_cookie(response)
        return response


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="获取当前账号基本信息",
        description=(
            "推荐使用 Authorization: Bearer <Access Token>；同时兼容 "
            "X-Token: <Access Token>。两者同时存在时必须一致。"
        ),
        responses={200: CurrentUserResponseSerializer},
        tags=["authentication"],
    )
    def get(self, request):
        return api_response(
            request,
            data=serialize_user(request.user),
            message="当前账号获取成功",
        )


class RemoteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="读取当前登录账号的远程 SCM 账号快照",
        description=(
            "使用当前用户在项目系统库中的 SCM 身份映射，对 "
            "scm_remote.eb_merchant_admin 执行固定参数化只读查询。"
            "仅返回当前账号的白名单字段，不返回密码哈希，也不接受远程表名、"
            "用户 ID 或商户 ID 参数。"
        ),
        responses={200: RemoteAccountResponseSerializer},
        tags=["authentication"],
    )
    def get(self, request):
        return api_response(
            request,
            data=remote_account_for_user(request.user),
            message="远程 SCM 账号数据读取成功",
        )
