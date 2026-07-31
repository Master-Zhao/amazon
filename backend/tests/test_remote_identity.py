from unittest.mock import patch

import bcrypt
from django.test import override_settings

from integrations.identity import scm


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.parameters = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, parameters):
        self.sql = sql
        self.parameters = parameters

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


@override_settings(
    REMOTE_SCM_AUTH_ENABLED=True,
    DATABASES={"default": {}, "scm_remote": {}},
)
def test_scm_identity_provider_uses_parameterized_read_only_lookup():
    encoded = bcrypt.hashpw(b"remote-test-password", bcrypt.gensalt())
    cursor = FakeCursor(
        [(155, 122, "W0765", encoded.decode("ascii"), 1, 0)]
    )
    provider = scm.SCMIdentityProvider()

    with patch.object(
        scm,
        "connections",
        {"scm_remote": FakeConnection(cursor)},
    ):
        identity = provider.authenticate(
            identifier="W0765",
            password="remote-test-password",
        )

    assert identity == scm.SCMIdentity(
        external_user_id="155",
        merchant_id="122",
        identifier="W0765",
        is_active=True,
    )
    assert "FROM eb_merchant_admin" in cursor.sql
    assert "BINARY account = BINARY %s" in cursor.sql
    assert cursor.parameters == ["W0765"]
    assert "remote-test-password" not in cursor.sql


@override_settings(
    REMOTE_SCM_AUTH_ENABLED=True,
    DATABASES={"default": {}, "scm_remote": {}},
)
def test_scm_identity_provider_rejects_wrong_password_and_duplicate_account():
    encoded = bcrypt.hashpw(b"correct-password", bcrypt.gensalt())
    wrong_password_cursor = FakeCursor(
        [(155, 122, "W0765", encoded.decode("ascii"), 1, 0)]
    )
    duplicate_cursor = FakeCursor(
        [
            (155, 122, "W0765", encoded.decode("ascii"), 1, 0),
            (156, 123, "W0765", encoded.decode("ascii"), 1, 0),
        ]
    )
    provider = scm.SCMIdentityProvider()

    with patch.object(
        scm,
        "connections",
        {"scm_remote": FakeConnection(wrong_password_cursor)},
    ):
        assert (
            provider.authenticate(
                identifier="W0765",
                password="wrong-password",
            )
            is None
        )

    with patch.object(
        scm,
        "connections",
        {"scm_remote": FakeConnection(duplicate_cursor)},
    ):
        assert (
            provider.authenticate(
                identifier="W0765",
                password="correct-password",
            )
            is None
        )


@override_settings(DATABASES={"default": {}, "scm_remote": {}})
def test_scm_account_snapshot_uses_exact_parameterized_read_only_lookup():
    cursor = FakeCursor([(155, 122, "W0765", 1, 0)])
    provider = scm.SCMIdentityProvider()

    with patch.object(
        scm,
        "connections",
        {"scm_remote": FakeConnection(cursor)},
    ):
        snapshot = provider.account_snapshot(
            external_user_id="155",
            merchant_id="122",
            identifier="W0765",
        )

    assert snapshot == scm.SCMAccountSnapshot(
        external_user_id="155",
        merchant_id="122",
        identifier="W0765",
        is_active=True,
    )
    assert "FROM eb_merchant_admin" in cursor.sql
    assert "merchant_admin_id = %s" in cursor.sql
    assert "mer_id = %s" in cursor.sql
    assert "BINARY account = BINARY %s" in cursor.sql
    assert "pwd" not in cursor.sql
    assert cursor.parameters == ["155", "122", "W0765"]
