from django.urls import include, path

from api.v1.views import PlatformInfoView

urlpatterns = [
    path("", PlatformInfoView.as_view(), name="api-v1-root"),
    path("auth/", include("apps.accounts.urls")),
]
