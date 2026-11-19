from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from .models import OrganizationMember, Project
from .permissions import get_member, get_project, organizations_for
from .serializers import (
    OrganizationSerializer,
    ProjectKeySerializer,
    ProjectSerializer,
    UserSerializer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request: Request) -> Response:
    """Sets the `csrftoken` cookie so the SPA can send `X-CSRFToken`."""
    return Response({"detail": "ok"})


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request: Request) -> Response:
    user = authenticate(
        request._request,
        username=str(request.data.get("email", "")).lower(),
        password=str(request.data.get("password", "")),
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
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
def organization_list(request: Request) -> Response:
    orgs = organizations_for(request.user).order_by("name")  # type: ignore[arg-type]
    return Response(OrganizationSerializer(orgs, many=True).data)


@api_view(["GET", "POST"])
def project_list(request: Request, org_slug: str) -> Response:
    member = get_member(request.user, org_slug)  # type: ignore[arg-type]
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
    project = get_project(request.user, org_slug, project_slug)  # type: ignore[arg-type]
    return Response(ProjectKeySerializer(project.keys.order_by("id"), many=True).data)
