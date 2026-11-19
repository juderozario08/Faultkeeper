"""Create (or refresh) the demo organization, projects, keys, and admin user.

Demo keys are deterministic so the demo apps can ship with a working default DSN.
Never use these keys outside local development.
"""

import hashlib
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from organizations.models import Organization, OrganizationMember, Project, ProjectKey, User

DEMO_EMAIL = "admin@faultkeeper.local"
DEMO_PASSWORD = "faultkeeper"

DEMO_PROJECTS = [
    ("Buggy Shop", "buggy-shop", "javascript"),
    ("Buggy Shop API", "buggy-shop-api", "python"),
]


def demo_key(project_slug: str) -> str:
    return hashlib.md5(f"faultkeeper-demo:{project_slug}".encode()).hexdigest()


class Command(BaseCommand):
    help = "Seed the demo organization, projects, DSN keys, and admin user."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        user = User.objects.filter(email=DEMO_EMAIL).first()
        if user is None:
            user = User.objects.create_superuser(DEMO_EMAIL, DEMO_PASSWORD, name="Demo Admin")

        org, _ = Organization.objects.get_or_create(slug="demo", defaults={"name": "Demo"})
        OrganizationMember.objects.get_or_create(
            organization=org, user=user, defaults={"role": OrganizationMember.Role.OWNER}
        )

        self.stdout.write(self.style.SUCCESS(f"Login: {DEMO_EMAIL} / {DEMO_PASSWORD}"))
        for name, slug, platform in DEMO_PROJECTS:
            project, _ = Project.objects.get_or_create(
                organization=org, slug=slug, defaults={"name": name, "platform": platform}
            )
            key, _ = ProjectKey.objects.get_or_create(
                public_key=demo_key(slug), defaults={"project": project, "label": "Demo"}
            )
            self.stdout.write(f"{slug:16s} DSN: {key.dsn()}")
