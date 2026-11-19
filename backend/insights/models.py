from django.db import models

from issues.models import Group


class IssueInsight(models.Model):
    """Cached LLM analysis of an issue (latest row wins)."""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="insights")
    provider = models.CharField(max_length=32)
    model = models.CharField(max_length=128)
    summary = models.TextField()
    root_cause = models.TextField()
    suggested_fix = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["group", "-created_at"], name="insight_group_created")]

    def __str__(self) -> str:
        return f"Insight for {self.group_id} ({self.provider}/{self.model})"
