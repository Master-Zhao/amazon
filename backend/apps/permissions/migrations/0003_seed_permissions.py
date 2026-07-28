from django.db import migrations


PERMISSIONS = {
    "reports.upload": "上传和重处理报表",
    "reports.view": "查看导入任务与错误",
    "advertising.view": "查看标准化广告主数据",
    "products.view": "查看产品与 Listing",
    "products.manage": "管理产品与 Listing",
    "analytics.view": "查看广告指标与异常",
    "analytics.configure": "配置目标 ACOS 与异常规则",
    "analysis.run": "运行智能分析",
    "recommendations.view": "查看优化建议",
    "actions.operate": "创建和提交 Action Preview",
    "approvals.approve": "审批优化方案",
    "executions.execute": "回填人工执行结果",
    "audit.view": "查看业务审计",
    "rbac.manage": "管理角色和授权",
    "knowledge.view": "查看知识中心",
}


def seed_permissions(apps, schema_editor):
    permission_model = apps.get_model("permissions", "Permission")
    for code, name in PERMISSIONS.items():
        permission_model.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "description": name,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("permissions", "0002_permission_description")]

    operations = [migrations.RunPython(seed_permissions, migrations.RunPython.noop)]
