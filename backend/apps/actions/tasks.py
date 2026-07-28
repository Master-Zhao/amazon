from celery import shared_task

from apps.actions.models import ExecutionTask
from apps.actions.services import evaluate_execution


@shared_task
def evaluate_effects(execution_task_id):
    task = ExecutionTask.objects.get(pk=execution_task_id)
    evaluation = evaluate_execution(task)
    return {"evaluationId": str(evaluation.pk)}

