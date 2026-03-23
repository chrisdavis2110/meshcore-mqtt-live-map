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
