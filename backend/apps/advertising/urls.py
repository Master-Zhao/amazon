from django.urls import path

from apps.advertising.views import CampaignListView, SearchTermListView, TargetingListView

urlpatterns = [
    path("campaigns", CampaignListView.as_view()),
    path("targeting", TargetingListView.as_view()),
    path("search-terms", SearchTermListView.as_view()),
]
