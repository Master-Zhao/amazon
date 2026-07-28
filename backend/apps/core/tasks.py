import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
    soft_time_limit=10,
    time_limit=15,
    name="apps.core.tasks.smoke_task",
)
def smoke_task(self, request_id: str) -> dict[str, str]:
    logger.info(
        "Celery smoke task completed",
        extra={"request_id": request_id, "task_id": self.request.id},
    )
    return {
        "status": "ok",
        "request_id": request_id,
        "task_id": str(self.request.id),
    }
