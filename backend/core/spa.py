"""Serve the built dashboard from Django (hosted demo, ADR 0007).

Same origin as the API, so session cookies are first-party in every browser
(Safari and Firefox block cross-site cookies). WhiteNoise serves the static
assets from FRONTEND_DIST; this view returns index.html for client-side routes.
"""

from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.views.decorators.cache import never_cache


@never_cache
def spa_index(request: HttpRequest, path: str = "") -> HttpResponse:
    dist = settings.FRONTEND_DIST
    index = Path(dist) / "index.html" if dist else None
    if index is None or not index.is_file():
        raise Http404("Dashboard build not found (set FRONTEND_DIST).")
    return HttpResponse(index.read_bytes(), content_type="text/html; charset=utf-8")
