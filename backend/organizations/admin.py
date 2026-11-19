from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Organization, OrganizationMember, Project, ProjectKey, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "name", "is_staff", "is_active")
    search_fields = ("email", "name")
    fieldsets = (
        (None, {"fields": ("email", "password", "name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


class MemberInline(admin.TabularInline):
    model = OrganizationMember
    extra = 0


class ProjectKeyInline(admin.TabularInline):
    model = ProjectKey
    extra = 0
    readonly_fields = ("public_key",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MemberInline]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("slug", "organization", "platform", "created_at")
    list_filter = ("organization",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProjectKeyInline]
