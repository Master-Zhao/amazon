import uuid

from django.db import models


class KnowledgeCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "knowledge_category"


class KnowledgeArticle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        KnowledgeCategory, on_delete=models.PROTECT, related_name="articles"
    )
    slug = models.SlugField(max_length=128, unique=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    published = models.BooleanField(default=True)

    class Meta:
        db_table = "knowledge_article"

