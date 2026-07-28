import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Idempotently create or update the local Phase 2A demo account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default=os.environ.get("DEMO_USER_EMAIL", "demo@example.invalid"),
        )
        parser.add_argument(
            "--username",
            default=os.environ.get("DEMO_USER_USERNAME", "demo"),
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("DEMO_USER_PASSWORD"),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        if not password:
            raise CommandError(
                "Provide --password or set DEMO_USER_PASSWORD; "
                "the command has no built-in password."
            )

        user_model = get_user_model()
        email = user_model.objects.normalize_email(options["email"])
        user = user_model.objects.filter(email__iexact=email).first()
        created = user is None
        if created:
            user = user_model(email=email, username=options["username"])
        else:
            user.email = email
            user.username = options["username"]

        user.set_password(password)
        user.is_active = True
        user.save()
        outcome = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Demo account {outcome}: {email}"))
