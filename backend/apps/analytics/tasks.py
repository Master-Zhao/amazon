from celery import shared_task

from apps.analytics.models import CampaignDailyMetric
from apps.analytics.services import evaluate_campaign_metric


@shared_task
def recalculate_anomalies(profile_id: str):
    count = 0
    for metric in CampaignDailyMetric.objects.filter(
        campaign__profile_id=profile_id
    ).iterator(chunk_size=500):
        evaluate_campaign_metric(metric)
        count += 1
    return {"processed": count}

