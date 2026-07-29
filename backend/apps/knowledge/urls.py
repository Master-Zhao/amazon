from django.urls import path

from apps.knowledge.views import (
    KnowledgeArticleDetailView,
    KnowledgeArticleListView,
    KnowledgeCategoryListView,
)

urlpatterns = [
    path(
        "tenants/<str:tenant_id>/categories",
        KnowledgeCategoryListView.as_view(),
        name="knowledge-category-list",
    ),
    path(
        "tenants/<str:tenant_id>/articles",
        KnowledgeArticleListView.as_view(),
        name="knowledge-article-list",
    ),
    path(
        "tenants/<str:tenant_id>/articles/<str:slug>",
        KnowledgeArticleDetailView.as_view(),
        name="knowledge-article-detail",
    ),
]
