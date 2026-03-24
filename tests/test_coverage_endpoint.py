import asyncio
import json

import pytest

import app


class _DummyResponse:
  def __init__(self, payload, status_code=200, request_url="https://coverage.example.com/get-samples"):
    self._payload = payload
    self.status_code = status_code
    self.request_url = request_url

  def raise_for_status(self):
    if self.status_code >= 400:
      request = app.httpx.Request("GET", self.request_url)
      response = app.httpx.Response(
        self.status_code,
        request=request,
        content=json.dumps(self._payload).encode("utf-8"),
        headers={"content-type": "application/json"},
      )
      raise app.httpx.HTTPStatusError(
        f"HTTP {self.status_code}",
        request=request,
        response=response,
      )
    return None

  def json(self):
    return self._payload


class _DummyClient:
  def __init__(self, response=None, exc=None):
    self._response = response
    self._exc = exc
    self.last_url = None

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type, exc, tb):
    return False

  async def get(self, _url):
    self.last_url = _url
    if self._exc is not None:
      raise self._exc
    return self._response


class _SequenceClient:
  def __init__(self, responses):
    self.responses = list(responses)
    self.last_url = None
    self.call_count = 0

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type, exc, tb):
    return False

  async def get(self, _url):
    self.last_url = _url
    self.call_count += 1
    if not self.responses:
      raise AssertionError("No more queued responses")
    response = self.responses.pop(0)
    if isinstance(response, Exception):
      raise response
    response.request_url = _url
    return response


def _json_body(response):
  if isinstance(response, app.JSONResponse):
    return json.loads(response.body)
  return response


@pytest.fixture(autouse=True)
def clear_coverage_cache():
  app.coverage_cache["provider"] = None
  app.coverage_cache["data"] = None
  app.coverage_cache["fetched_at"] = 0.0
  app.coverage_cache["cooldown_until"] = 0.0
  app.coverage_cache["last_error"] = None
  app.coverage_cache["source"] = None
  app.coverage_cache["region"] = None
  app.coverage_cache["generated_at"] = None
  yield
  app.coverage_cache["provider"] = None
  app.coverage_cache["data"] = None
  app.coverage_cache["fetched_at"] = 0.0
  app.coverage_cache["cooldown_until"] = 0.0
  app.coverage_cache["last_error"] = None
  app.coverage_cache["source"] = None
  app.coverage_cache["region"] = None
  app.coverage_cache["generated_at"] = None


def test_filter_coverage_by_age_uses_30_day_default(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_MAX_AGE_DAYS", 30.0)
  now = 1_700_000_000.0
  fresh = {"timestamp": now - (10 * 86400)}
  stale = {"timestamp": now - (45 * 86400)}
  legacy_fresh = {"time": now - (5 * 86400)}
  legacy_stale = {"time": now - (40 * 86400)}
  unknown = {"grid_id": "no_ts"}

  result = app._filter_coverage_by_age(
    [fresh, stale, legacy_fresh, legacy_stale, unknown],
    now=now,
  )

  assert result == [fresh, legacy_fresh, unknown]


def test_filter_coverage_by_age_zero_disables_filter(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_MAX_AGE_DAYS", 0.0)
  data = [{"timestamp": 1}, {"time": 2}]

  result = app._filter_coverage_by_age(data, now=1000.0)

  assert result == data


def test_coverage_requires_config(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "")

  with pytest.raises(app.HTTPException) as exc:
    asyncio.run(app.get_coverage())
  assert exc.value.status_code == 503
  assert "coverage_api_not_configured" in exc.value.detail


def test_coverage_success_returns_keys_array(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "")
  dummy = _DummyClient(response=_DummyResponse({"keys": [{"hash": "ABCD12"}]}))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  result = _json_body(asyncio.run(app.get_coverage()))
  assert isinstance(result, list)
  assert result == [{"hash": "ABCD12"}]
  assert dummy.last_url == "https://coverage.example.com/get-samples"


def test_coverage_non_list_keys_returns_empty_array(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "")
  dummy = _DummyClient(response=_DummyResponse({"keys": {"hash": "ABCD12"}}))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  result = _json_body(asyncio.run(app.get_coverage()))
  assert result == []


def test_coverage_list_payload_is_supported(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "")
  dummy = _DummyClient(response=_DummyResponse([{"hash": "ABCD12"}]))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  result = _json_body(asyncio.run(app.get_coverage()))
  assert result == [{"hash": "ABCD12"}]


def test_coverage_timeout_maps_to_504(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "")
  timeout_exc = app.httpx.TimeoutException("timeout")
  dummy = _DummyClient(exc=timeout_exc)
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  with pytest.raises(app.HTTPException) as exc:
    asyncio.run(app.get_coverage())
  assert exc.value.status_code == 504
  assert exc.value.detail == "coverage_api_timeout"


def test_coverage_http_error_maps_to_502(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "")
  dummy = _DummyClient(response=_DummyResponse({"keys": []}, status_code=500))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  with pytest.raises(app.HTTPException) as exc:
    asyncio.run(app.get_coverage())
  assert exc.value.status_code == 502
  assert "coverage_api_error: HTTP 500" in exc.value.detail


def test_meshmapper_domain_uses_coverage_php_with_key(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://meshmapper.net")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "abc123")
  payload = {
    "success": True,
    "grid_squares": [
      {
        "grid_id": "1_2",
        "bounds": {
          "south": 42.0,
          "west": -71.0,
          "north": 42.01,
          "east": -70.99,
        },
        "coverage_type": "BIDIR",
        "fill_color": "#1e7e34",
        "border_color": "#14522d",
        "snr": 8.5,
        "timestamp": 1710547200,
      }
    ],
  }
  dummy = _DummyClient(response=_DummyResponse(payload))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  result, provider, meta = asyncio.run(app._fetch_coverage_upstream())

  assert result == payload["grid_squares"]
  assert provider == "meshmapper"
  assert meta.get("region") is None
  assert dummy.last_url == "https://meshmapper.net/coverage.php?key=abc123"


def test_meshmapper_full_url_preserves_existing_key(monkeypatch):
  monkeypatch.setattr(
    app,
    "COVERAGE_API_URL",
    "https://meshmapper.net/coverage.php?key=from-url",
  )
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "from-env")
  payload = {"success": True, "grid_squares": []}
  dummy = _DummyClient(response=_DummyResponse(payload))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  result, provider, meta = asyncio.run(app._fetch_coverage_upstream())

  assert result == []
  assert provider == "meshmapper"
  assert meta["provider"] == "meshmapper"
  assert dummy.last_url == "https://meshmapper.net/coverage.php?key=from-url"


def test_meshmapper_sync_writes_local_cache_file(monkeypatch, tmp_path):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://meshmapper.net")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "abc123")
  monkeypatch.setattr(app, "COVERAGE_CACHE_FILE", str(tmp_path / "coverage_cache.json"))
  now = {"value": 1000.0}
  monkeypatch.setattr(app.time, "time", lambda: now["value"])
  payload = {
    "success": True,
    "region": "BOS",
    "generated_at": 1710548200,
    "grid_squares": [{"grid_id": "1_2", "bounds": {"south": 1, "west": 2, "north": 3, "east": 4}}],
  }
  client = _SequenceClient([_DummyResponse(payload)])
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: client)

  result = asyncio.run(app._sync_meshmapper_coverage_once())

  assert result is True
  saved = json.loads((tmp_path / "coverage_cache.json").read_text(encoding="utf-8"))
  assert saved["provider"] == "meshmapper"
  assert saved["region"] == "BOS"
  assert saved["generated_at"] == 1710548200.0
  assert saved["data"] == payload["grid_squares"]
  assert saved["fetched_at"] == 1000.0


def test_meshmapper_get_coverage_reads_local_cache_file_without_upstream(monkeypatch, tmp_path):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://meshmapper.net")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "abc123")
  monkeypatch.setattr(app, "COVERAGE_MAX_AGE_DAYS", 30.0)
  cache_file = tmp_path / "coverage_cache.json"
  monkeypatch.setattr(app, "COVERAGE_CACHE_FILE", str(cache_file))
  now = {"value": 1_700_000_000.0}
  monkeypatch.setattr(app.time, "time", lambda: now["value"])
  payload = {
    "provider": "meshmapper",
    "region": "BOS",
    "generated_at": 1700000100.0,
    "fetched_at": 1000.0,
    "cooldown_until": 0.0,
    "last_error": None,
    "data": [
      {
        "grid_id": "1_2",
        "bounds": {"south": 1, "west": 2, "north": 3, "east": 4},
        "timestamp": now["value"] - (5 * 86400),
      },
      {
        "grid_id": "1_3",
        "bounds": {"south": 1, "west": 2, "north": 3, "east": 4},
        "timestamp": now["value"] - (45 * 86400),
      },
    ],
  }
  cache_file.write_text(json.dumps(payload), encoding="utf-8")
  client = _SequenceClient([])
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: client)

  first_response = asyncio.run(app.get_coverage())
  second_response = asyncio.run(app.get_coverage())
  first = _json_body(first_response)
  second = _json_body(second_response)

  assert first == [payload["data"][0]]
  assert second == [payload["data"][0]]
  assert client.call_count == 0
  assert app.coverage_cache["source"] == "file"
  assert first_response.headers["X-Coverage-Provider"] == "meshmapper"
  assert first_response.headers["X-Coverage-Region"] == "BOS"


def test_meshmapper_rate_limit_uses_cached_data_and_cooldown(monkeypatch, tmp_path):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://meshmapper.net")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "abc123")
  monkeypatch.setattr(app, "COVERAGE_RATE_LIMIT_COOLDOWN_SECONDS", 600)
  monkeypatch.setattr(app, "COVERAGE_CACHE_FILE", str(tmp_path / "coverage_cache.json"))
  now = {"value": 1000.0}
  monkeypatch.setattr(app.time, "time", lambda: now["value"])
  success_payload = {
    "success": True,
    "grid_squares": [{"grid_id": "1_2", "bounds": {"south": 1, "west": 2, "north": 3, "east": 4}}],
  }
  rate_limit_payload = {
    "success": False,
    "error": "rate_limit_exceeded",
    "message": "Daily request limit reached",
    "resets_in_hours": 2,
  }
  client = _SequenceClient([
    _DummyResponse(success_payload),
    _DummyResponse(rate_limit_payload, status_code=429),
  ])
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: client)

  first = asyncio.run(app._sync_meshmapper_coverage_once())
  now["value"] = 1005.0
  second = asyncio.run(app._sync_meshmapper_coverage_once())
  now["value"] = 1010.0
  third = _json_body(asyncio.run(app.get_coverage()))

  assert first is True
  assert second is True
  assert third == success_payload["grid_squares"]
  assert client.call_count == 2
  assert app.coverage_cache["cooldown_until"] == 1005.0 + 7200


def test_meshmapper_rate_limit_without_cache_returns_429(monkeypatch, tmp_path):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://meshmapper.net")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "abc123")
  monkeypatch.setattr(app, "COVERAGE_RATE_LIMIT_COOLDOWN_SECONDS", 600)
  monkeypatch.setattr(app, "COVERAGE_CACHE_FILE", str(tmp_path / "coverage_cache_empty.json"))
  now = {"value": 1000.0}
  monkeypatch.setattr(app.time, "time", lambda: now["value"])
  rate_limit_payload = {
    "success": False,
    "error": "rate_limit_exceeded",
    "message": "Daily request limit reached",
    "resets_in_hours": 1.5,
  }
  client = _SequenceClient([
    _DummyResponse(rate_limit_payload, status_code=429),
  ])
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: client)

  result = asyncio.run(app._sync_meshmapper_coverage_once())

  assert result is False
  assert app.coverage_cache["cooldown_until"] == 1000.0 + 5400

  with pytest.raises(app.HTTPException) as exc:
    asyncio.run(app.get_coverage())

  assert exc.value.status_code == 429
  assert "coverage_rate_limited" in exc.value.detail


def test_meshmapper_get_coverage_without_local_cache_returns_503(monkeypatch, tmp_path):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://meshmapper.net")
  monkeypatch.setattr(app, "COVERAGE_CACHE_FILE", str(tmp_path / "missing.json"))
  with pytest.raises(app.HTTPException) as exc:
    asyncio.run(app.get_coverage())
  assert exc.value.status_code == 503
  assert exc.value.detail == "coverage_cache_empty"


def test_legacy_get_coverage_filters_stale_items(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  monkeypatch.setattr(app, "COVERAGE_API_KEY", "")
  monkeypatch.setattr(app, "COVERAGE_MAX_AGE_DAYS", 30.0)
  now = {"value": 1_700_000_000.0}
  monkeypatch.setattr(app.time, "time", lambda: now["value"])
  payload = [
    {"hash": "NEW", "time": now["value"] - (10 * 86400)},
    {"hash": "OLD", "time": now["value"] - (45 * 86400)},
  ]
  dummy = _DummyClient(response=_DummyResponse(payload))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  response = asyncio.run(app.get_coverage())
  result = _json_body(response)

  assert result == [payload[0]]
  assert response.headers["X-Coverage-Provider"] == "legacy"
