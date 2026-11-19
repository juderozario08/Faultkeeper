from django.db import models

from organizations.models import Project


class Release(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="releases")
    version = models.CharField(max_length=250)
    first_seen = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "version"], name="unique_release_version")
        ]

    def __str__(self) -> str:
        return self.version


class Environment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="environments")
    name = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="unique_environment_name")
        ]

    def __str__(self) -> str:
        return self.name


class Group(models.Model):
    """An issue: all events that share a grouping hash."""

    class Status(models.TextChoices):
        UNRESOLVED = "unresolved"
        RESOLVED = "resolved"
        IGNORED = "ignored"

    class Substatus(models.TextChoices):
        NEW = "new"
        ONGOING = "ongoing"
        REGRESSED = "regressed"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="groups")
    title = models.CharField(max_length=255)
    culprit = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=32, default="error")  # error | default (message)
    level = models.CharField(max_length=16, default="error")
    platform = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UNRESOLVED)
    substatus = models.CharField(max_length=16, choices=Substatus.choices, default=Substatus.NEW)
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()
    times_seen = models.PositiveIntegerField(default=1)
    first_release = models.ForeignKey(Release, null=True, blank=True, on_delete=models.SET_NULL)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["project", "status", "-last_seen"], name="group_project_status_seen"
            ),
        ]

    def __str__(self) -> str:
        return self.title


class GroupHash(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    hash = models.CharField(max_length=32)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="hashes")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "hash"], name="unique_group_hash")
        ]

    def __str__(self) -> str:
        return self.hash


class Event(models.Model):
    """One occurrence. `payload` is the full normalized event (our nodestore)."""

    event_id = models.UUIDField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="events")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="events")
    timestamp = models.DateTimeField()
    received_at = models.DateTimeField()
    level = models.CharField(max_length=16)
    platform = models.CharField(max_length=64, blank=True)
    release = models.CharField(max_length=250, blank=True)
    environment = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=255)
    payload = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "event_id"], name="unique_project_event")
        ]
        indexes = [
            models.Index(fields=["group", "-timestamp"], name="event_group_ts"),
            models.Index(fields=["project", "-timestamp"], name="event_project_ts"),
        ]

    def __str__(self) -> str:
        return f"{self.event_id.hex} {self.title}"
