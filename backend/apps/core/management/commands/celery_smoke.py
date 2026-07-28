import uuid

from django.core.management.base import BaseCommand, CommandError

from apps.core.tasks import smoke_task


class Command(BaseCommand):
    help = "Dispatch a non-business Celery smoke task and verify its result."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=15)

    def handle(self, *args, **options):
        request_id = f"req_smoke_{uuid.uuid4().hex}"
        async_result = smoke_task.apply_async(args=[request_id])
        try:
            result = async_result.get(timeout=options["timeout"])
        except Exception as exc:
            raise CommandError(
                f"Celery smoke task did not complete: {type(exc).__name__}"
            ) from exc
        if result.get("status") != "ok" or result.get("request_id") != request_id:
            raise CommandError("Celery smoke task returned an invalid result")
        self.stdout.write(
            self.style.SUCCESS(
                f"Celery smoke succeeded taskId={async_result.id} requestId={request_id}"
            )
        )
