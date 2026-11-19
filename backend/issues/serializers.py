from typing import Any

from rest_framework import serializers

from .models import Event, Group


class GroupSerializer(serializers.ModelSerializer[Group]):
    project = serializers.SerializerMethodField()
    first_release = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            "id",
            "title",
            "culprit",
            "type",
            "level",
            "platform",
            "status",
            "substatus",
            "first_seen",
            "last_seen",
            "times_seen",
            "first_release",
            "project",
        ]

    def get_project(self, obj: Group) -> dict[str, Any]:
        return {"id": obj.project_id, "slug": obj.project.slug}

    def get_first_release(self, obj: Group) -> str | None:
        return obj.first_release.version if obj.first_release else None


class StatusUpdateSerializer(serializers.Serializer[None]):
    status = serializers.ChoiceField(choices=Group.Status.choices)


class EventSummarySerializer(serializers.ModelSerializer[Event]):
    event_id = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ["event_id", "timestamp", "level", "release", "environment", "title", "platform"]

    def get_event_id(self, obj: Event) -> str:
        return obj.event_id.hex


class EventDetailSerializer(EventSummarySerializer):
    payload = serializers.JSONField()
    group_id = serializers.IntegerField()

    class Meta(EventSummarySerializer.Meta):
        fields = [*EventSummarySerializer.Meta.fields, "group_id", "received_at", "payload"]
