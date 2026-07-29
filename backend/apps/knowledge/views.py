import hashlib

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.knowledge.models import KnowledgeArticle, KnowledgeCategory
from apps.permissions.services import require_membership


class KnowledgeCategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiResponse(description="知识分类列表")}, tags=["knowledge"])
    def get(self, request, tenant_id):
        require_membership(user=request.user, tenant_id=tenant_id)
        categories = KnowledgeCategory.objects.order_by("order")
        return api_response(
            request,
            data=[
                {
                    "code": category.code,
                    "name": category.name,
                    "description": "",
                    "sortOrder": category.order,
                }
                for category in categories
            ],
        )


class KnowledgeArticleListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="knowledge_article_list",
        responses={200: OpenApiResponse(description="知识文章列表")},
        tags=["knowledge"],
    )
    def get(self, request, tenant_id):
        require_membership(user=request.user, tenant_id=tenant_id)
        category_code = request.query_params.get("category")
        articles = KnowledgeArticle.objects.select_related("category").filter(
            published=True,
        )
        if category_code:
            articles = articles.filter(category__code=category_code)
        articles = articles.order_by("category__order", "title")
        return api_response(
            request,
            data=[
                {
                    "slug": article.slug,
                    "title": article.title,
                    "summary": "",
                    "categoryCode": article.category.code,
                    "categoryName": article.category.name,
                    "sortOrder": 0,
                    "updatedAt": article.created_at.isoformat() if hasattr(article, "created_at") else "",
                    "body": article.body,
                    "contentHash": hashlib.sha256(article.body.encode("utf-8")).hexdigest(),
                }
                for article in articles
            ],
        )


class KnowledgeArticleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="knowledge_article_detail",
        responses={200: OpenApiResponse(description="知识文章详情")},
        tags=["knowledge"],
    )
    def get(self, request, tenant_id, slug):
        require_membership(user=request.user, tenant_id=tenant_id)
        article = (
            KnowledgeArticle.objects.select_related("category")
            .filter(slug=slug, published=True)
            .first()
        )
        if article is None:
            raise NotFound("文章不存在")
        return api_response(
            request,
            data={
                "slug": article.slug,
                "title": article.title,
                "summary": "",
                "categoryCode": article.category.code,
                "categoryName": article.category.name,
                "sortOrder": 0,
                "updatedAt": article.created_at.isoformat() if hasattr(article, "created_at") else "",
                "body": article.body,
                "contentHash": hashlib.sha256(article.body.encode("utf-8")).hexdigest(),
            },
        )
