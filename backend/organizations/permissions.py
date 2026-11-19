from django.db.models import QuerySet
from django.http import Http404

from .models import Organization, OrganizationMember, Project, User


def organizations_for(user: User) -> QuerySet[Organization]:
    return Organization.objects.filter(members__user=user)


def get_member(user: User, org_slug: str) -> OrganizationMember:
    """Return the user's membership, or 404 so foreign orgs are indistinguishable from missing."""
    try:
        return OrganizationMember.objects.select_related("organization").get(
            organization__slug=org_slug, user=user
        )
    except OrganizationMember.DoesNotExist as exc:
        raise Http404 from exc


def get_project(user: User, org_slug: str, project_slug: str) -> Project:
    try:
        return Project.objects.select_related("organization").get(
            organization__slug=org_slug,
            organization__members__user=user,
            slug=project_slug,
        )
    except Project.DoesNotExist as exc:
        raise Http404 from exc


def user_can_access_project(user: User, project_id: int) -> bool:
    return Project.objects.filter(id=project_id, organization__members__user=user).exists()
