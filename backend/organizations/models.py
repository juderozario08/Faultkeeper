import secrets
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager

    from issues.models import Environment, Event, Group, Release


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> "User":
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> "User":
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Logs in with email, like Sentry."""

    # Attributes Django adds at runtime, declared for editors/type checkers.
    id: int
    memberships: "RelatedManager[OrganizationMember]"

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []  # type: ignore[var-annotated]

    def __str__(self) -> str:
        return self.email


class Organization(models.Model):
    id: int
    members: "RelatedManager[OrganizationMember]"
    projects: "RelatedManager[Project]"

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.slug


class OrganizationMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner"
        ADMIN = "admin"
        MEMBER = "member"

    id: int
    organization_id: int
    user_id: int

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="unique_org_member")
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.organization} ({self.role})"


class Project(models.Model):
    id: int
    organization_id: int
    keys: "RelatedManager[ProjectKey]"
    releases: "RelatedManager[Release]"
    environments: "RelatedManager[Environment]"
    groups: "RelatedManager[Group]"
    events: "RelatedManager[Event]"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50)
    platform = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "slug"], name="unique_project_slug")
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.slug}"


def generate_public_key() -> str:
    return secrets.token_hex(16)  # 32 lowercase hex chars


class ProjectKey(models.Model):
    """A DSN key. SDKs authenticate with `public_key`."""

    id: int
    project_id: int

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="keys")
    label = models.CharField(max_length=64, default="Default")
    public_key = models.CharField(max_length=32, unique=True, default=generate_public_key)
    is_active = models.BooleanField(default=True)
    rate_limit_per_minute = models.PositiveIntegerField(default=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.project} [{self.label}]"

    def dsn(self, base_url: str | None = None) -> str:
        """`scheme://public_key@host[:port]/project_id`."""
        parts = urlsplit(base_url or settings.FAULTKEEPER_PUBLIC_URL)
        return f"{parts.scheme}://{self.public_key}@{parts.netloc}/{self.project_id}"
