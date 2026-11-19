from pathlib import Path

import pytest
from django.test import Client, override_settings

from core.spa import spa_index


@pytest.mark.django_db
def test_spa_index_serves_built_dashboard(tmp_path: Path, rf) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "index.html").write_text("<div id=root></div>")
    with override_settings(FRONTEND_DIST=str(tmp_path)):
        response = spa_index(rf.get("/demo/web/issues"), "demo/web/issues")
    assert response.status_code == 200
    assert b"id=root" in response.content


@pytest.mark.django_db
def test_spa_index_missing_build_is_404(client: Client, rf) -> None:  # type: ignore[no-untyped-def]
    from django.http import Http404

    with override_settings(FRONTEND_DIST=""), pytest.raises(Http404):
        spa_index(rf.get("/"))
