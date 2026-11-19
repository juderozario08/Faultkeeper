from django.contrib import admin
from django.urls import include, path

from core.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/0/health/", health, name="health"),
    path("api/0/", include("organizations.urls")),
    path("api/0/", include("issues.urls")),
    path("api/0/", include("insights.urls")),
    path("", include("ingest.urls")),
]
