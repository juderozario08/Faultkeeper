from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from core.spa import spa_index
from core.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/0/health/", health, name="health"),
    path("api/0/", include("organizations.urls")),
    path("api/0/", include("issues.urls")),
    path("api/0/", include("insights.urls")),
    path("", include("ingest.urls")),
]

if settings.FRONTEND_DIST:
    # Client-side routes of the dashboard (everything that isn't API/admin/static).
    urlpatterns += [re_path(r"^(?!api/|admin/|static/|ws/).*$", spa_index)]
