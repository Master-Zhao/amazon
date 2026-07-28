from django.db import migrations


PERMISSIONS = {
    "context.view": "查看卖家空间上下文",
    "members.manage": "管理成员",
    "roles.manage": "管理角色",
    "stores.manage": "管理店铺",
    "profiles.manage": "管理广告 Profile",
    "reports.view": "查看报表",
    "reports.import": "导入报表",
    "analytics.view": "查看广告分析",
    "analysis.run": "运行智能分析",
    "recommendations.view": "查看建议",
    "actions.submit": "提交动作方案",
    "actions.approve": "审批动作方案",
    "actions.execute": "回填人工执行",
    "audit.view": "查看审计日志",
    "knowledge.view": "查看知识中心",
}


def seed_permissions(apps, schema_editor):
    permission_model = apps.get_model("permissions", "Permission")
    for code, name in PERMISSIONS.items():
        permission_model.objects.update_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("permissions", "0001_initial")]

    operations = [migrations.RunPython(seed_permissions, migrations.RunPython.noop)]

