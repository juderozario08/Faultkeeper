from rest_framework import serializers

from .models import Organization, Project, ProjectKey, User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "email", "name"]


class OrganizationSerializer(serializers.ModelSerializer[Organization]):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "created_at"]


class ProjectSerializer(serializers.ModelSerializer[Project]):
    organization = serializers.CharField(source="organization.slug", read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "slug", "platform", "organization", "created_at"]


class ProjectKeySerializer(serializers.ModelSerializer[ProjectKey]):
    dsn = serializers.SerializerMethodField()

    class Meta:
        model = ProjectKey
        fields = ["id", "label", "public_key", "dsn", "is_active", "rate_limit_per_minute"]
        read_only_fields = ["public_key", "dsn"]

    def get_dsn(self, obj: ProjectKey) -> str:
        return obj.dsn()
