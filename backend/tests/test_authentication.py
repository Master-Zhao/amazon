import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import (
    AuthenticationAuditEvent,
    ExternalIdentity,
    ExternalIdentitySource,
    RefreshTokenRecord,
)
from integrations.identity.scm import (
    RemoteIdentityProviderUnavailable,
    SCMIdentity,
)

PASSWORD = "test-only-strong-password"


@pytest.fixture
def user():
    return get_user_model().objects.create_user(
        username="phase2a-user",
        email="User@Example.INVALID",
        password=PASSWORD,
    )


def login(
    client: APIClient,
    *,
    email="user@example.invalid",
    identifier=None,
    password=PASSWORD,
):
    credentials = {"password": password}
    if identifier is not None:
        credentials["identifier"] = identifier
    elif email is not None:
        credentials["email"] = email
    return client.post(
        "/api/v1/auth/login",
        credentials,
        format="json",
    )


def bearer(client: APIClient, access_token: str) -> None:
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")


def x_token(client: APIClient, access_token: str) -> None:
    client.credentials(HTTP_X_TOKEN=access_token)


@pytest.mark.django_db
def test_login_returns_access_and_string_user_id_but_never_refresh_json(user):
    response = login(APIClient())

    assert response.status_code == 200
    assert response.json()["data"]["user"]["id"] == str(user.pk)
    assert isinstance(response.json()["data"]["accessToken"], str)
    assert "refreshToken" not in json.dumps(response.json())


@pytest.mark.django_db
def test_login_is_case_insensitive_and_user_email_is_normalized(user):
    response = login(APIClient(), email="  USER@example.invalid  ")

    user.refresh_from_db()
    assert response.status_code == 200
    assert user.email == "user@example.invalid"


@pytest.mark.django_db
def test_login_accepts_identifier_for_alphanumeric_username():
    user = get_user_model().objects.create_user(
        username="W0765",
        email="w0765@example.invalid",
        password=PASSWORD,
    )

    response = login(APIClient(), identifier="  W0765  ")

    assert response.status_code == 200
    assert response.json()["data"]["user"]["id"] == str(user.pk)


@pytest.mark.django_db
def test_login_keeps_legacy_email_request_compatible(user):
    response = login(APIClient(), email="USER@example.invalid")

    assert response.status_code == 200
    assert response.json()["data"]["user"]["id"] == str(user.pk)


@pytest.mark.django_db
@override_settings(REMOTE_SCM_AUTH_ENABLED=True)
@patch("apps.accounts.services.SCMIdentityProvider.authenticate")
def test_remote_scm_login_provisions_passwordless_local_identity(authenticate):
    authenticate.return_value = SCMIdentity(
        external_user_id="155",
        merchant_id="122",
        identifier="W0765",
        is_active=True,
    )

    response = login(
        APIClient(),
        identifier="W0765",
        password="remote-password-not-stored",
    )

    assert response.status_code == 200
    user = get_user_model().objects.get(username="W0765")
    identity = ExternalIdentity.objects.get(user=user)
    assert user.has_usable_password() is False
    assert identity.source == ExternalIdentitySource.SCM_MERCHANT_ADMIN
    assert identity.external_user_id == "155"
    assert identity.external_merchant_id == "122"
    assert identity.identifier == "W0765"
    assert RefreshTokenRecord.objects.filter(user=user).count() == 1
    authenticate.assert_called_once_with(
        identifier="W0765",
        password="remote-password-not-stored",
    )


@pytest.mark.django_db
@override_settings(REMOTE_SCM_AUTH_ENABLED=True)
@patch("apps.accounts.services.SCMIdentityProvider.authenticate")
def test_remote_scm_login_reuses_existing_local_identity(authenticate):
    authenticate.return_value = SCMIdentity(
        external_user_id="155",
        merchant_id="122",
        identifier="W0765",
        is_active=True,
    )
    client = APIClient()

    first = login(client, identifier="W0765", password="remote-password")
    second = login(client, identifier="W0765", password="remote-password")

    assert first.status_code == second.status_code == 200
    assert get_user_model().objects.filter(username="W0765").count() == 1
    assert ExternalIdentity.objects.count() == 1


@pytest.mark.django_db
@override_settings(REMOTE_SCM_AUTH_ENABLED=True)
@patch("apps.accounts.services.SCMIdentityProvider.authenticate")
def test_remote_scm_login_does_not_take_over_colliding_local_user(authenticate):
    local_user = get_user_model().objects.create_user(
        username="W0765",
        email="local-w0765@example.invalid",
        password=PASSWORD,
    )
    authenticate.return_value = SCMIdentity(
        external_user_id="155",
        merchant_id="122",
        identifier="W0765",
        is_active=True,
    )

    response = login(
        APIClient(),
        identifier="W0765",
        password="remote-password",
    )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"
    assert ExternalIdentity.objects.count() == 0
    assert get_user_model().objects.get(pk=local_user.pk).has_usable_password()
    authenticate.assert_not_called()


@pytest.mark.django_db
@override_settings(REMOTE_SCM_AUTH_ENABLED=True)
@patch("apps.accounts.services.SCMIdentityProvider.authenticate")
def test_remote_scm_disabled_account_cannot_login(authenticate):
    authenticate.return_value = SCMIdentity(
        external_user_id="155",
        merchant_id="122",
        identifier="W0765",
        is_active=False,
    )

    response = login(
        APIClient(),
        identifier="W0765",
        password="remote-password",
    )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_USER_DISABLED"
    assert ExternalIdentity.objects.count() == 0


@pytest.mark.django_db
@override_settings(REMOTE_SCM_AUTH_ENABLED=True)
@patch("apps.accounts.services.SCMIdentityProvider.authenticate")
def test_remote_scm_outage_returns_retryable_service_error(authenticate):
    authenticate.side_effect = RemoteIdentityProviderUnavailable()

    response = login(
        APIClient(),
        identifier="W0765",
        password="remote-password",
    )

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_NOT_READY"
    assert response.json()["message"] == "远程账号服务暂不可用"
    assert AuthenticationAuditEvent.objects.get().outcome == (
        "provider_unavailable"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("payload", "expected_field"),
    [
        ({"password": PASSWORD}, "identifier"),
        ({"identifier": "   ", "password": PASSWORD}, "identifier"),
        (
            {
                "identifier": "phase2a-user",
                "email": "user@example.invalid",
                "password": PASSWORD,
            },
            "identifier",
        ),
        (
            {
                "identifier": "phase2a-user",
                "password": PASSWORD,
                "unexpected": "value",
            },
            "unexpected",
        ),
    ],
)
def test_login_rejects_invalid_identifier_contract(
    user,
    payload,
    expected_field,
):
    response = APIClient().post(
        "/api/v1/auth/login",
        payload,
        format="json",
    )

    assert response.status_code == 400
    assert expected_field in response.json()["data"]["errors"]
    assert "accessToken" not in json.dumps(response.json())


@pytest.mark.django_db
def test_invalid_password_and_unknown_email_share_the_same_error(user):
    client = APIClient()
    wrong_password = login(client, password="wrong-password")
    unknown_email = login(
        client,
        email="missing@example.invalid",
        password="wrong-password",
    )

    expected = ("AUTH_INVALID_CREDENTIALS", "账号或密码错误")
    assert (
        wrong_password.json()["code"],
        wrong_password.json()["message"],
    ) == expected
    assert (
        unknown_email.json()["code"],
        unknown_email.json()["message"],
    ) == expected


@pytest.mark.django_db
def test_inactive_user_cannot_login(user):
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = login(APIClient())

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_USER_DISABLED"


@pytest.mark.django_db
def test_refresh_cookie_has_required_attributes(user):
    response = login(APIClient())
    cookie = response.cookies[settings.JWT_REFRESH_COOKIE_NAME]

    assert cookie["httponly"] is True
    assert cookie["path"] == "/api/v1/auth/"
    assert cookie["samesite"] == settings.JWT_COOKIE_SAME_SITE
    assert bool(cookie["secure"]) is settings.JWT_COOKIE_SECURE
    assert int(cookie["max-age"]) == settings.JWT_REFRESH_TOKEN_TTL_DAYS * 86400


@pytest.mark.django_db
def test_refresh_requires_cookie(user):
    response = APIClient().post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_MISSING"
    assert response.json()["requestId"].startswith("req_")


@pytest.mark.django_db
def test_refresh_rejects_forged_token(user):
    client = APIClient()
    login_response = login(client)
    raw_token = login_response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
    header, payload, signature = raw_token.split(".")
    forged_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = (
        f"{header}.{payload}.{forged_signature}"
    )

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_INVALID"


@pytest.mark.django_db
def test_refresh_rejects_expired_token(user):
    token = RefreshToken.for_user(user)
    token["user_id"] = str(user.pk)
    token.set_exp(lifetime=timedelta(seconds=-1))
    raw_token = str(token)
    RefreshTokenRecord.objects.create(
        token_hash=__import__("hashlib").sha256(raw_token.encode()).hexdigest(),
        user=user,
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    client = APIClient()
    client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = raw_token

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_EXPIRED"


@pytest.mark.django_db
def test_refresh_rotates_cookie_and_revokes_previous_token(user):
    client = APIClient()
    login_response = login(client)
    old_token = login_response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value

    response = client.post("/api/v1/auth/refresh")
    new_token = response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value

    assert response.status_code == 200
    assert response.json()["data"]["accessToken"]
    assert "refreshToken" not in json.dumps(response.json())
    assert new_token != old_token

    client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = old_token
    revoked_response = client.post("/api/v1/auth/refresh")
    assert revoked_response.status_code == 401
    assert revoked_response.json()["code"] == "AUTH_TOKEN_REVOKED"


@pytest.mark.django_db
@override_settings(JWT_ROTATE_REFRESH_TOKENS=False)
def test_refresh_rotation_can_be_disabled(user):
    client = APIClient()
    login_response = login(client)
    old_token = login_response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert settings.JWT_REFRESH_COOKIE_NAME not in response.cookies
    assert client.cookies[settings.JWT_REFRESH_COOKIE_NAME].value == old_token


@pytest.mark.django_db
def test_logout_revokes_refresh_and_is_idempotent(user):
    client = APIClient()
    login_response = login(client)
    raw_token = login_response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value

    first = client.post("/api/v1/auth/logout")
    client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = raw_token
    second = client.post("/api/v1/auth/logout")

    assert first.status_code == second.status_code == 200
    assert first.cookies[settings.JWT_REFRESH_COOKIE_NAME]["max-age"] == 0
    assert RefreshTokenRecord.objects.get().revoked_at is not None


@pytest.mark.django_db
def test_revoked_refresh_cannot_be_reused_after_logout(user):
    client = APIClient()
    raw_token = login(client).cookies[settings.JWT_REFRESH_COOKIE_NAME].value
    client.post("/api/v1/auth/logout")
    client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = raw_token

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_REVOKED"


@pytest.mark.django_db
def test_me_requires_access_token(user):
    response = APIClient().get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


@pytest.mark.django_db
def test_me_returns_only_basic_account_fields(user):
    client = APIClient()
    access_token = login(client).json()["data"]["accessToken"]
    bearer(client, access_token)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "id": str(user.pk),
        "email": "user@example.invalid",
        "username": user.username,
        "firstName": "",
        "lastName": "",
    }
    response_text = json.dumps(response.json()).lower()
    assert "password" not in response_text
    assert "tenant" not in response_text
    assert "role" not in response_text


@pytest.mark.django_db
def test_me_accepts_access_token_from_x_token_header(user):
    client = APIClient()
    access_token = login(client).json()["data"]["accessToken"]
    x_token(client, access_token)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(user.pk)


@pytest.mark.django_db
def test_me_accepts_matching_authorization_and_x_token_headers(user):
    client = APIClient()
    access_token = login(client).json()["data"]["accessToken"]
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        HTTP_X_TOKEN=access_token,
    )

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200


@pytest.mark.django_db
def test_me_rejects_conflicting_authentication_headers(user):
    client = APIClient()
    access_token = login(client).json()["data"]["accessToken"]
    other_token = str(AccessToken.for_user(user))
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
        HTTP_X_TOKEN=other_token,
    )

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_INVALID"
    assert response.json()["message"] == "认证标头中的访问令牌不一致"


@pytest.mark.django_db
def test_me_rejects_expired_access_token(user):
    token = AccessToken.for_user(user)
    token.set_exp(lifetime=timedelta(seconds=-1))
    client = APIClient()
    bearer(client, str(token))

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_EXPIRED"


@pytest.mark.django_db
def test_me_rejects_forged_and_refresh_tokens(user):
    client = APIClient()
    access_token = login(client).json()["data"]["accessToken"]
    header, payload, signature = access_token.split(".")
    forged_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    bearer(client, f"{header}.{payload}.{forged_signature}")
    forged = client.get("/api/v1/auth/me")

    bearer(client, str(RefreshToken.for_user(user)))
    wrong_type = client.get("/api/v1/auth/me")

    assert forged.json()["code"] == "AUTH_TOKEN_INVALID"
    assert wrong_type.json()["code"] == "AUTH_TOKEN_INVALID"


@pytest.mark.django_db
def test_disabled_user_is_rejected_after_access_was_issued(user):
    client = APIClient()
    access_token = login(client).json()["data"]["accessToken"]
    user.is_active = False
    user.save(update_fields=["is_active"])
    bearer(client, access_token)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_USER_DISABLED"


@pytest.mark.django_db
def test_auth_audit_stores_hashes_and_request_ids_not_credentials(user):
    client = APIClient()
    client.credentials(HTTP_X_REQUEST_ID="req_auth_audit")
    login(client)

    event = AuthenticationAuditEvent.objects.get(event="login")
    serialized = json.dumps(
        {
            "event": event.event,
            "outcome": event.outcome,
            "email_hash": event.email_hash,
            "request_id": event.request_id,
        }
    )
    assert event.request_id == "req_auth_audit"
    assert user.email not in serialized
    assert PASSWORD not in serialized
    assert len(event.email_hash) == 64


@pytest.mark.django_db
def test_failed_login_audit_is_append_only_and_contains_no_plain_email(user):
    client = APIClient()
    client.credentials(HTTP_X_REQUEST_ID="req_failed_login")

    login(client, password="wrong-password")

    event = AuthenticationAuditEvent.objects.get(
        event="login",
        outcome="invalid_credentials",
    )
    assert event.request_id == "req_failed_login"
    assert event.email_hash != user.email
    assert len(event.email_hash) == 64


@pytest.mark.django_db
def test_request_log_does_not_include_password_or_tokens(user, caplog):
    client = APIClient()
    response = login(client)
    access_token = response.json()["data"]["accessToken"]

    log_output = "\n".join(record.getMessage() for record in caplog.records)
    assert PASSWORD not in log_output
    assert access_token not in log_output
    assert response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value not in log_output


@pytest.mark.django_db
def test_openapi_contains_all_auth_paths_and_bearer_scheme(user):
    schema = APIClient().get("/api/schema/", HTTP_ACCEPT="application/json").json()

    for path in (
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
    ):
        assert path in schema["paths"]
    assert schema["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"
    assert schema["components"]["securitySchemes"]["xTokenAuth"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-Token",
        "description": (
            "Access Token compatibility header. When Authorization is also "
            "present, both token values must match."
        ),
    }
    me_security = schema["paths"]["/api/v1/auth/me"]["get"]["security"]
    assert {"bearerAuth": []} in me_security
    assert {"xTokenAuth": []} in me_security


@pytest.mark.django_db
def test_seed_demo_user_requires_password_and_is_idempotent():
    with pytest.raises(CommandError):
        call_command("seed_demo_user", email="seed@example.invalid")

    call_command(
        "seed_demo_user",
        email="Seed@Example.INVALID",
        username="seed",
        password=PASSWORD,
    )
    call_command(
        "seed_demo_user",
        email="seed@example.invalid",
        username="seed-renamed",
        password=PASSWORD,
    )

    users = get_user_model().objects.filter(email="seed@example.invalid")
    assert users.count() == 1
    assert users.get().username == "seed-renamed"
    assert users.get().check_password(PASSWORD)
