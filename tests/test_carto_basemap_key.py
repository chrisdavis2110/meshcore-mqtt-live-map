from pathlib import Path

from fastapi.testclient import TestClient

import app


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_JS = REPO_ROOT / "backend" / "static" / "app.js"
APP_PY = REPO_ROOT / "backend" / "app.py"


def test_dark_preview_carto_url_includes_encoded_api_key():
  url = app._preview_tile_url(
    "dark", 8, 77, 94, api_key="domain key/+"
  )

  assert url == (
    "https://a.basemaps.cartocdn.com/dark_all/8/77/94.png"
    "?key=domain+key%2F%2B"
  )


def test_dark_preview_falls_back_without_api_key():
  assert app._preview_tile_url("dark", 8, 77, 94, api_key="") == (
    "https://tile.openstreetmap.org/8/77/94.png"
  )


def test_map_page_exposes_configured_carto_key(monkeypatch):
  monkeypatch.setattr(app, "CARTO_BASEMAP_KEY", "public-test-key")
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)

  response = TestClient(app.app).get("/")

  assert response.status_code == 200
  assert 'data-carto-basemap-key="public-test-key"' in response.text


def test_browser_only_requests_carto_when_key_is_configured():
  source = APP_JS.read_text(encoding="utf-8")

  assert source.index("const cleanConfigValue") < source.index(
    "const cartoBasemapKey"
  )
  assert "config.cartoBasemapKey" in source
  assert "encodeURIComponent(cartoBasemapKey)" in source
  assert "const darkTiles = cartoBasemapKey" in source


def test_preview_errors_do_not_log_key_bearing_tile_url():
  source = APP_PY.read_text(encoding="utf-8")

  assert "from {tile_url}" not in source
