from fastapi.testclient import TestClient

import app


def test_root_injects_weather_flags(monkeypatch):
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)
  monkeypatch.setattr(app, "WEATHER_RADAR_ENABLED", False)
  monkeypatch.setattr(app, "WEATHER_WIND_ENABLED", True)
  monkeypatch.setattr(app, "APP_VERSION", "9.9.9-test")

  client = TestClient(app.app)
  response = client.get("/")

  assert response.status_code == 200
  assert 'data-app-version="9.9.9-test"' in response.text
  assert 'data-weather-radar-enabled="false"' in response.text
  assert 'data-weather-wind-enabled="true"' in response.text


def test_root_injects_both_weather_flags_off(monkeypatch):
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)
  monkeypatch.setattr(app, "WEATHER_RADAR_ENABLED", False)
  monkeypatch.setattr(app, "WEATHER_WIND_ENABLED", False)

  client = TestClient(app.app)
  response = client.get("/")

  assert response.status_code == 200
  assert 'data-weather-radar-enabled="false"' in response.text
  assert 'data-weather-wind-enabled="false"' in response.text


def test_root_injects_boundary_config(monkeypatch):
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)
  monkeypatch.setattr(app, "MAP_BOUNDARY_MODE", "polygon")
  monkeypatch.setattr(app, "MAP_BOUNDARY_SHOW", True)
  monkeypatch.setattr(app, "get_map_boundary_name", lambda: "Test Boundary")
  monkeypatch.setattr(app, "get_map_boundary_points", lambda: [(42.1, -71.1), (42.2, -71.2), (42.3, -71.1)])

  client = TestClient(app.app)
  response = client.get("/")

  assert response.status_code == 200
  assert 'data-map-boundary-mode="polygon"' in response.text
  assert 'data-map-boundary-show="true"' in response.text
  assert 'data-map-boundary-name="Test Boundary"' in response.text
  assert '<script id="map-boundary-data" type="application/json">[[42.1, -71.1], [42.2, -71.2], [42.3, -71.1]]</script>' in response.text


def test_root_injects_qr_code_button_flag(monkeypatch):
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)
  monkeypatch.setattr(app, "QR_CODE_BUTTON_ENABLED", True)

  client = TestClient(app.app)
  response = client.get("/")

  assert response.status_code == 200
  assert 'data-qr-code-button-enabled="true"' in response.text


def test_root_injects_los_curvature_defaults(monkeypatch):
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)
  monkeypatch.setattr(app, "LOS_CURVATURE_ENABLED", True)
  monkeypatch.setattr(app, "LOS_CURVATURE_FACTOR", 1.333333)

  client = TestClient(app.app)
  response = client.get("/")

  assert response.status_code == 200
  assert 'data-los-curvature-enabled="true"' in response.text
  assert 'data-los-curvature-factor="1.333333"' in response.text


def test_map_injects_route_history_and_peer_defaults(monkeypatch):
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)
  monkeypatch.setattr(app, "ROUTE_HISTORY_ENABLED", True)
  monkeypatch.setattr(app, "ROUTE_BYTE_FILTER_DEFAULT", "2b,3b")
  monkeypatch.setattr(app, "HISTORY_BYTE_FILTER_DEFAULT", "1b")
  monkeypatch.setattr(app, "PEERS_DEFAULT_OPEN", True)

  client = TestClient(app.app)
  response = client.get("/map")

  assert response.status_code == 200
  assert response.headers.get("cache-control") == "no-store"
  assert 'data-route-history-enabled="true"' in response.text
  assert 'data-route-byte-filter-default="2b,3b"' in response.text
  assert 'data-history-byte-filter-default="1b"' in response.text
  assert 'data-peers-default-open="true"' in response.text
  assert "{{ROUTE_HISTORY_ENABLED}}" not in response.text
  assert "{{ROUTE_BYTE_FILTER_DEFAULT}}" not in response.text
  assert "{{HISTORY_BYTE_FILTER_DEFAULT}}" not in response.text
  assert "{{PEERS_DEFAULT_OPEN}}" not in response.text


def test_map_coordinate_embed_includes_preview_image(monkeypatch):
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)

  client = TestClient(app.app)
  response = client.get("/map?lat=42.13306&lon=-71.67163")

  assert response.status_code == 200
  assert 'property="og:image"' in response.text
  assert '/preview.png?lat=42.13306&amp;lon=-71.67163' in response.text
  assert 'name="twitter:image"' in response.text
  assert (
    'property="og:url" content="http://testserver/map?lat=42.13306'
    '&amp;lon=-71.67163"'
  ) in response.text
