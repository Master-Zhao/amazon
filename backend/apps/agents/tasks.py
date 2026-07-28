from celery import shared_task

from apps.agents.services import run_orchestrator


@shared_task(bind=True, autoretry_for=(OSError,), retry_kwargs={"max_retries": 2})
def run_analysis_task(self, task_id):
    run_orchestrator(task_id)
    return {"taskId": task_id}

