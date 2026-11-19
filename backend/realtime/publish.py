"""Publish issue changes to dashboards watching the project."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from issues.models import Group

from .consumers import project_group_name


def publish_group_update(group: Group, created: bool) -> None:
    from issues.serializers import GroupSerializer

    layer = get_channel_layer()
    if layer is None:
        return
    payload = {
        "type": "issue.created" if created else "issue.updated",
        "issue": GroupSerializer(group).data,
    }
    async_to_sync(layer.group_send)(
        project_group_name(group.project_id), {"type": "issue.update", "payload": payload}
    )
