from celery import shared_task

from apps.analytics.services import recalculate_profile_anomalies


@shared_task
def recalculate_anomalies(profile_id: str):
    return {"processed": recalculate_profile_anomalies(profile_id)}
