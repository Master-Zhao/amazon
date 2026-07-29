from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationType
from apps.tenants.models import Tenant, TenantMembership


class Command(BaseCommand):
    help = "Idempotently seed demo notification data"

    def handle(self, *args, **options):
        demo_user = User.objects.filter(email="demo@example.invalid").first()
        if demo_user is None:
            self.stdout.write(
                self.style.WARNING("No demo@example.invalid user found, skipping")
            )
            return

        membership = TenantMembership.objects.filter(
            user=demo_user, is_active=True,
        ).select_related("tenant").first()
        if membership is None:
            self.stdout.write(self.style.WARNING("No active membership found, skipping"))
            return

        tenant = membership.tenant

        existing = Notification.objects.filter(
            recipient=demo_user, tenant=tenant,
        ).count()
        if existing > 0:
            self.stdout.write(self.style.SUCCESS(f"Notifications already exist ({existing}), skipping"))
            return

        now = timezone.now()
        notifications = [
            Notification(
                tenant=tenant,
                recipient=demo_user,
                notification_type=NotificationType.ANOMALY_DETECTED,
                title="ACOS 异常预警",
                content="Campaign 'Summer Sale SP' 的 ACOS 达到 45.2%，超过目标值 30%，建议检查关键词和竞价。",
                target_route="/advertising/overview",
                is_read=False,
            ),
            Notification(
                tenant=tenant,
                recipient=demo_user,
                notification_type=NotificationType.APPROVAL_REQUIRED,
                title="预算调整待审批",
                content="AI 建议将 Campaign 'Brand Keywords' 日预算从 $50 调整为 $35，请审批。",
                target_route="/actions",
                is_read=False,
            ),
            Notification(
                tenant=tenant,
                recipient=demo_user,
                notification_type=NotificationType.REPORT_IMPORTED,
                title="Campaign 报表导入完成",
                content="2026-07-28 Campaign 报表已成功导入，共 156 条记录。",
                target_route="/reports/imports",
                is_read=False,
            ),
            Notification(
                tenant=tenant,
                recipient=demo_user,
                notification_type=NotificationType.ANALYSIS_COMPLETE,
                title="AI 分析完成",
                content="数据分析 Agent 已完成本轮分析，生成 3 条优化建议。",
                target_route="/analysis",
                is_read=True,
                read_at=now,
            ),
            Notification(
                tenant=tenant,
                recipient=demo_user,
                notification_type=NotificationType.ACTION_EXECUTED,
                title="竞价调整已执行",
                content="关键词 'running shoes' 竞价从 $1.20 调整为 $0.95，执行成功。",
                target_route="/actions",
                is_read=True,
                read_at=now,
            ),
        ]

        Notification.objects.bulk_create(notifications)
        self.stdout.write(self.style.SUCCESS(f"Created {len(notifications)} demo notifications"))
