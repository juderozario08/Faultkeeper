from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.csrf),
    path("auth/login/", views.login_view),
    path("auth/logout/", views.logout_view),
    path("auth/me/", views.me),
    path("organizations/", views.organization_list),
    path("organizations/<slug:org_slug>/projects/", views.project_list),
    path("projects/<slug:org_slug>/<slug:project_slug>/keys/", views.project_key_list),
]
