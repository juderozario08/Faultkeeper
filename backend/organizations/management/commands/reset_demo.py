"""Delete all issues/events in the demo organization (projects, keys and users stay).

Handy before a live demo: `docker compose exec web python manage.py reset_demo`.
"""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from issues.models import Environment, Group, Release


class Command(BaseCommand):
    help = "Remove all issues, events, releases and environments from the demo organization."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--org", default="demo")

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        org = options["org"]
        groups, _ = Group.objects.filter(project__organization__slug=org).delete()
        Release.objects.filter(project__organization__slug=org).delete()
        Environment.objects.filter(project__organization__slug=org).delete()
        self.stdout.write(self.style.SUCCESS(f"Cleared demo data for '{org}' ({groups} rows)."))
