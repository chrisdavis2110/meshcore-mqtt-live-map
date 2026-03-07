import asyncio

import pytest

import app


class _DummyResponse:
  def __init__(self, payload, status_code=200):
    self._payload = payload
    self.status_code = status_code

  def raise_for_status(self):
    if self.status_code >= 400:
      request = app.httpx.Request("GET", "https://coverage.example.com/get-samples")
      response = app.httpx.Response(self.status_code, request=request)
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

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type, exc, tb):
    return False

  async def get(self, _url):
    if self._exc is not None:
      raise self._exc
    return self._response


def test_coverage_requires_config(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "")

  with pytest.raises(app.HTTPException) as exc:
    asyncio.run(app.get_coverage())
  assert exc.value.status_code == 503
  assert "coverage_api_not_configured" in exc.value.detail


def test_coverage_success_returns_keys_array(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  dummy = _DummyClient(response=_DummyResponse({"keys": [{"hash": "ABCD12"}]}))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  result = asyncio.run(app.get_coverage())
  assert isinstance(result, list)
  assert result == [{"hash": "ABCD12"}]


def test_coverage_non_list_keys_returns_empty_array(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  dummy = _DummyClient(response=_DummyResponse({"keys": {"hash": "ABCD12"}}))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  result = asyncio.run(app.get_coverage())
  assert result == []


def test_coverage_list_payload_is_supported(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  dummy = _DummyClient(response=_DummyResponse([{"hash": "ABCD12"}]))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  result = asyncio.run(app.get_coverage())
  assert result == [{"hash": "ABCD12"}]


def test_coverage_timeout_maps_to_504(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  timeout_exc = app.httpx.TimeoutException("timeout")
  dummy = _DummyClient(exc=timeout_exc)
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  with pytest.raises(app.HTTPException) as exc:
    asyncio.run(app.get_coverage())
  assert exc.value.status_code == 504
  assert exc.value.detail == "coverage_api_timeout"


def test_coverage_http_error_maps_to_502(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  dummy = _DummyClient(response=_DummyResponse({"keys": []}, status_code=500))
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  with pytest.raises(app.HTTPException) as exc:
    asyncio.run(app.get_coverage())
  assert exc.value.status_code == 502
  assert "coverage_api_error: HTTP 500" in exc.value.detail
