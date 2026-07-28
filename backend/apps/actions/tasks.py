from celery import shared_task

from apps.actions.services import evaluate_execution


@shared_task
def evaluate_effects(execution_task_id):
    evaluation = evaluate_execution(execution_task_id)
    return {"evaluationId": str(evaluation.pk)}
