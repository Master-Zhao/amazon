from django.urls import path

from apps.knowledge.views import KnowledgeListView

urlpatterns = [path("", KnowledgeListView.as_view())]

