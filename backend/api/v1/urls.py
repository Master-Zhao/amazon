from django.urls import path

from api.v1.views import PlatformInfoView

urlpatterns = [
    path("", PlatformInfoView.as_view(), name="api-v1-root"),
]
