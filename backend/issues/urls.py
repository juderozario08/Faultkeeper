from django.urls import path

from . import views

urlpatterns = [
    path("projects/<slug:org_slug>/<slug:project_slug>/issues/", views.issue_list),
    path("projects/<slug:org_slug>/<slug:project_slug>/stats/", views.project_stats),
    path("projects/<slug:org_slug>/<slug:project_slug>/filters/", views.project_filters),
    path("issues/<int:issue_id>/", views.issue_detail),
    path("issues/<int:issue_id>/events/", views.issue_events),
    path("issues/<int:issue_id>/events/<str:event_id>/", views.issue_event_detail),
    path("issues/<int:issue_id>/tags/", views.issue_tags),
]
