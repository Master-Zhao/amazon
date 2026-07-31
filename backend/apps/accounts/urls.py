from django.urls import path

from apps.accounts.views import (
    CurrentUserView,
    LoginView,
    LogoutView,
    RefreshView,
    RemoteAccountView,
)

urlpatterns = [
    path("login", LoginView.as_view(), name="auth-login"),
    path("refresh", RefreshView.as_view(), name="auth-refresh"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("me", CurrentUserView.as_view(), name="auth-me"),
    path("remote-account", RemoteAccountView.as_view(), name="auth-remote-account"),
]
