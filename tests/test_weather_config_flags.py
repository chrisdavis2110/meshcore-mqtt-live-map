from fastapi.testclient import TestClient

import app


def test_root_injects_weather_flags(monkeypatch):
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)
  monkeypatch.setattr(app, "WEATHER_RADAR_ENABLED", False)
  monkeypatch.setattr(app, "WEATHER_WIND_ENABLED", True)

  client = TestClient(app.app)
  response = client.get("/")

  assert response.status_code == 200
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
