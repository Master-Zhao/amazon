from django.conf import settings
from django.db import models

from apps.tenants.models import Tenant


class NotificationType(models.TextChoices):
    SYSTEM = "SYSTEM", "System"
    ANALYSIS_COMPLETE = "ANALYSIS_COMPLETE", "Analysis Complete"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED", "Approval Required"
    ACTION_EXECUTED = "ACTION_EXECUTED", "Action Executed"
    REPORT_IMPORTED = "REPORT_IMPORTED", "Report Imported"
    ANOMALY_DETECTED = "ANOMALY_DETECTED", "Anomaly Detected"


class Notification(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    title = models.CharField(max_length=256)
    content = models.TextField(blank=True)
    target_route = models.CharField(max_length=512, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sys_notification"
        indexes = [
            models.Index(
                fields=["recipient", "-created_at"],
                name="sys_notif_rec_cr_idx",
            ),
            models.Index(
                fields=["recipient", "is_read"],
                name="sys_notif_rec_rd_idx",
            ),
            models.Index(
                fields=["tenant", "-created_at"],
                name="sys_notif_tn_cr_idx",
            ),
        ]