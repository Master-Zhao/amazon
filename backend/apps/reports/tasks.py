from celery import shared_task

from apps.reports.services import process_task


@shared_task(
    bind=True,
    autoretry_for=(OSError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
    acks_late=True,
)
def process_import_task(self, task_id: str):
    process_task(task_id)
    return {"taskId": task_id}

