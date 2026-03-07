from fastapi.testclient import TestClient

import app
import weather


class _DummyResponse:
  def __init__(self, payload, status_code=200):
    self._payload = payload
    self.status_code = status_code

  def raise_for_status(self):
    if self.status_code >= 400:
      request = app.httpx.Request("GET", "https://example.test")
      response = app.httpx.Response(self.status_code, request=request)
      raise app.httpx.HTTPStatusError(
        f"HTTP {self.status_code}",
        request=request,
        response=response,
      )

  def json(self):
    return self._payload


class _DummyAsyncClient:
  def __init__(self, calls, responses):
    self.calls = calls
    self.responses = responses

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type, exc, tb):
    return False

  async def get(self, url, params=None):
    self.calls.append((url, params))
    response = self.responses.get(url)
    if response is None:
      raise RuntimeError(f"unexpected_url: {url}")
    return response


def test_weather_country_bounds_rejects_invalid_coords(monkeypatch):
  monkeypatch.setattr(app, "PROD_MODE", False)
  client = TestClient(app.app)

  response = client.get(
    "/weather/radar/country-bounds",
    params={"lat": "nan", "lon": "-71.0"},
  )

  assert response.status_code == 400
  assert response.json().get("detail") == "invalid_coords"


def test_weather_country_bounds_requires_prod_token(monkeypatch):
  monkeypatch.setattr(app, "PROD_MODE", True)
  monkeypatch.setattr(app, "PROD_TOKEN", "secret-token")
  client = TestClient(app.app)

  response = client.get(
    "/weather/radar/country-bounds",
    params={"lat": "42.36", "lon": "-71.05"},
  )

  assert response.status_code == 401
  assert response.json().get("detail") == "unauthorized"


def test_weather_country_bounds_success_and_cache(monkeypatch):
  monkeypatch.setattr(app, "PROD_MODE", False)
  weather._radar_country_bounds_cache.clear()

  calls = []
  responses = {
    "https://api.bigdatacloud.net/data/reverse-geocode-client": _DummyResponse(
      {"countryCode": "US", "countryName": "United States"}
    ),
    "https://restcountries.com/v3.1/alpha/US": _DummyResponse([{"cca3": "USA"}]),
    "https://www.geoboundaries.org/api/current/gbOpen/USA/ADM0/": _DummyResponse(
      {"simplifiedGeometryGeoJSON": "https://example.test/usa.geo.json"}
    ),
    "https://example.test/usa.geo.json": _DummyResponse(
      {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "geometry": {
              "type": "Polygon",
              "coordinates": [[
                [-72.2, 41.8],
                [-70.0, 41.8],
                [-70.0, 43.0],
                [-72.2, 43.0],
                [-72.2, 41.8],
              ]],
            },
          }
        ],
      }
    ),
  }

  def fake_async_client(*_args, **_kwargs):
    return _DummyAsyncClient(calls=calls, responses=responses)

  monkeypatch.setattr(weather.httpx, "AsyncClient", fake_async_client)
  client = TestClient(app.app)

  first = client.get(
    "/weather/radar/country-bounds",
    params={"lat": "42.3601", "lon": "-71.0589"},
  )
  second = client.get(
    "/weather/radar/country-bounds",
    params={"lat": "42.3601", "lon": "-71.0589"},
  )

  assert first.status_code == 200
  assert second.status_code == 200
  payload = first.json()
  assert payload["country_code"] == "US"
  assert payload["country_iso3"] == "USA"
  assert payload["source"] == "bigdatacloud+geoboundaries"
  assert "bounds" in payload
  assert payload == second.json()

  call_urls = [url for url, _params in calls]
  assert call_urls.count(
    "https://api.bigdatacloud.net/data/reverse-geocode-client"
  ) == 2
  assert call_urls.count("https://restcountries.com/v3.1/alpha/US") == 1
  assert call_urls.count(
    "https://www.geoboundaries.org/api/current/gbOpen/USA/ADM0/"
  ) == 1
  assert call_urls.count("https://example.test/usa.geo.json") == 1
