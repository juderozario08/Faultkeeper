"""Publishing issue updates to WebSocket subscribers. Filled in by story 7.0."""

from issues.models import Group


def publish_group_update(group: Group, created: bool) -> None:
    return None
