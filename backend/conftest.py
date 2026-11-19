from collections.abc import Iterator

import pytest
from django.core.cache import cache

from organizations.models import Organization, Project, ProjectKey

PUBLIC_KEY = "0123456789abcdef0123456789abcdef"


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def project(db: None) -> Project:
    org = Organization.objects.create(name="Acme", slug="acme")
    return Project.objects.create(organization=org, name="Web", slug="web", platform="python")


@pytest.fixture
def project_key(project: Project) -> ProjectKey:
    return ProjectKey.objects.create(project=project, public_key=PUBLIC_KEY)
