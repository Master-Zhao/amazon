import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.notifications.models import Notification, NotificationType
from apps.tenants.models import Tenant, TenantMembership

User = get_user_model()


@pytest.mark.django_db
class TestNotificationAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(
        username="notifuser", email="notif@example.invalid", password="pass1234"
        )
        self.tenant = Tenant.objects.create(
            name="NotifTenant", tenant_type="PERSONAL"
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            membership_role="OWNER",
        )
        self.client = APIClient()

    def _authenticate(self):
        self.client.force_authenticate(user=self.user)

    def _create_notification(self, **kwargs):
        defaults = {
            "tenant": self.tenant,
            "recipient": self.user,
            "notification_type": NotificationType.SYSTEM,
            "title": "Test notification",
            "content": "Test content",
            "target_route": "/advertising/overview",
        }
        defaults.update(kwargs)
        return Notification.objects.create(**defaults)

    def test_list_notifications_unauthenticated(self):
        response = self.client.get("/api/v1/notifications", follow=True)
        assert response.status_code == 401

    def test_list_notifications_empty(self):
        self._authenticate()
        response = self.client.get("/api/v1/notifications", follow=True)
        assert response.status_code == 200
        assert response.data["code"] == "SUCCESS"
        assert response.data["data"] == []

    def test_list_notifications_with_data(self):
        self._authenticate()
        self._create_notification(title="First")
        self._create_notification(title="Second")
        response = self.client.get("/api/v1/notifications", follow=True)
        assert response.status_code == 200
        assert len(response.data["data"]) == 2

    def test_unread_count_empty(self):
        self._authenticate()
        response = self.client.get("/api/v1/notifications/unread-count", follow=True)
        assert response.status_code == 200
        assert response.data["data"]["unread_count"] == 0

    def test_unread_count_with_unread(self):
        self._authenticate()
        self._create_notification(is_read=False)
        self._create_notification(is_read=False)
        self._create_notification(is_read=True)
        response = self.client.get("/api/v1/notifications/unread-count", follow=True)
        assert response.status_code == 200
        assert response.data["data"]["unread_count"] == 2

    def test_mark_read(self):
        self._authenticate()
        notification = self._create_notification(is_read=False)
        response = self.client.post(
            f"/api/v1/notifications/{notification.id}/read", follow=True
        )
        assert response.status_code == 200
        notification.refresh_from_db()
        assert notification.is_read is True
        assert notification.read_at is not None

    def test_mark_read_already_read(self):
        self._authenticate()
        notification = self._create_notification(is_read=True)
        response = self.client.post(
            f"/api/v1/notifications/{notification.id}/read", follow=True
        )
        assert response.status_code == 200

    def test_mark_read_not_found(self):
        self._authenticate()
        response = self.client.post("/api/v1/notifications/99999/read", follow=True)
        assert response.status_code == 404

    def test_mark_all_read(self):
        self._authenticate()
        self._create_notification(is_read=False)
        self._create_notification(is_read=False)
        self._create_notification(is_read=True)
        response = self.client.post("/api/v1/notifications/read-all", follow=True)
        assert response.status_code == 200
        assert response.data["data"]["marked_count"] == 2
        assert Notification.objects.filter(recipient=self.user, is_read=False).count() == 0

    def test_cross_tenant_isolation(self):
        other_user = User.objects.create_user(
        username="otheruser", email="other@example.invalid", password="pass1234"
        )
        other_tenant = Tenant.objects.create(
            name="OtherTenant", tenant_type="PERSONAL"
        )
        TenantMembership.objects.create(
            tenant=other_tenant,
            user=other_user,
            membership_role="OWNER",
        )
        self._create_notification(title="Mine")
        Notification.objects.create(
            tenant=other_tenant,
            recipient=other_user,
            notification_type=NotificationType.SYSTEM,
            title="Theirs",
            content="Other content",
        )
        self._authenticate()
        response = self.client.get("/api/v1/notifications", follow=True)
        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["title"] == "Mine"
