from django.db import migrations


CONTENT = [
    ("metrics", "指标说明", "metrics-guide", "广告指标说明", "CTR、CPC、CVR、ACOS、ROAS 均由确定性公式计算。"),
    ("reports", "报表说明", "reports-guide", "三类报表说明", "Campaign、Targeting、Search Term 分别进入独立权威粒度。"),
    ("anomalies", "异常规则", "anomaly-guide", "异常规则说明", "数据不足返回 INSUFFICIENT_DATA，AI 不裁决异常。"),
    ("actions", "优化动作", "actions-guide", "优化动作说明", "批准后仅生成人工执行清单，不直接修改 Amazon。"),
    ("operations", "操作指南", "operation-guide", "操作指南", "先选择卖家空间和 Profile，再上传、分析、审批与回填。"),
    ("faq", "常见问题", "faq", "常见问题", "真实 Amazon 报表格式仍需脱敏样例最终校准。"),
]


def seed(apps, schema_editor):
    category_model = apps.get_model("knowledge", "KnowledgeCategory")
    article_model = apps.get_model("knowledge", "KnowledgeArticle")
    for index, (code, name, slug, title, body) in enumerate(CONTENT):
        category, _ = category_model.objects.get_or_create(
            code=code, defaults={"name": name, "order": index}
        )
        article_model.objects.get_or_create(
            slug=slug,
            defaults={"category": category, "title": title, "body": body, "published": True},
        )


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]

