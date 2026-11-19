from django.urls import path

from . import views

urlpatterns = [path("issues/<int:issue_id>/insights/", views.issue_insights)]
