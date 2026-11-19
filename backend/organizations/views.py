from typing import Any, cast

from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from .models import OrganizationMember, Project, User
from .permissions import get_member, get_project, organizations_for
from .serializers import (
    OrganizationSerializer,
    ProjectKeySerializer,
    ProjectSerializer,
    UserSerializer,
)


def current_user(request: Request) -> User:
    """Views behind IsAuthenticated always have a real User."""
    return cast(User, request.user)


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request: Request) -> Response:
    """Sets the `csrftoken` cookie so the SPA can send `X-CSRFToken`."""
    return Response({"detail": "ok"})


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request: Request) -> Response:
    data: dict[str, Any] = request.data if isinstance(request.data, dict) else {}
    user = authenticate(
        request._request,
        username=str(data.get("email", "")).lower(),
        password=str(data.get("password", "")),
    )
    if user is None:
        return Response({"detail": "Invalid email or password."}, status=400)
    login(request._request, user)
    return Response(UserSerializer(user).data)


@api_view(["POST"])
def logout_view(request: Request) -> Response:
    logout(request._request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def me(request: Request) -> Response:
    return Response(UserSerializer(current_user(request)).data)


@api_view(["GET"])
def organization_list(request: Request) -> Response:
    orgs = organizations_for(current_user(request)).order_by("name")
    return Response(OrganizationSerializer(orgs, many=True).data)


@api_view(["GET", "POST"])
def project_list(request: Request, org_slug: str) -> Response:
    member = get_member(current_user(request), org_slug)
    if request.method == "POST":
        if member.role == OrganizationMember.Role.MEMBER:
            return Response({"detail": "Only owners and admins can create projects."}, status=403)
        serializer = ProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(organization=member.organization)
        project.keys.create()
        return Response(ProjectSerializer(project).data, status=201)
    projects = Project.objects.filter(organization=member.organization).order_by("name")
    return Response(ProjectSerializer(projects, many=True).data)


@api_view(["GET"])
def project_key_list(request: Request, org_slug: str, project_slug: str) -> Response:
    project = get_project(current_user(request), org_slug, project_slug)
    return Response(ProjectKeySerializer(project.keys.order_by("id"), many=True).data)
