from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_response
from apps.knowledge.models import KnowledgeCategory


class KnowledgeListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiResponse(description="知识文章")}, tags=["knowledge"])
    def get(self, request):
        categories = KnowledgeCategory.objects.prefetch_related("articles").order_by("order")
        return api_response(
            request,
            data={
                "categories": [
                    {
                        "code": category.code,
                        "name": category.name,
                        "articles": [
                            {
                                "id": str(article.pk),
                                "slug": article.slug,
                                "title": article.title,
                                "body": article.body,
                            }
                            for article in category.articles.filter(published=True)
                        ],
                    }
                    for category in categories
                ]
            },
        )

