from django.urls import path

from . import views

urlpatterns = [
    path("api/<int:project_id>/envelope/", views.envelope_endpoint),
    path("api/<int:project_id>/store/", views.store_endpoint),
]
