from celery import shared_task

from apps.reports.services import process_report_import


@shared_task(
    bind=True,
    autoretry_for=(OSError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_import_task(self, task_id: int) -> str:
    task = process_report_import(task_id=task_id)
    return task.status
