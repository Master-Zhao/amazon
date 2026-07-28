from celery import shared_task

from apps.agents.services import process_agent_run


@shared_task(
    bind=True,
    autoretry_for=(OSError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def process_agent_run_task(self, run_id: int) -> str:
    return process_agent_run(run_id=run_id).status
