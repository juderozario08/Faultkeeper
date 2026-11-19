from django.contrib import admin

from .models import Event, Group


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "project", "level", "status", "times_seen", "last_seen")
    list_filter = ("project", "status", "level")
    search_fields = ("title", "culprit")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "title", "project", "level", "timestamp")
    list_filter = ("project", "level")
    raw_id_fields = ("group",)
