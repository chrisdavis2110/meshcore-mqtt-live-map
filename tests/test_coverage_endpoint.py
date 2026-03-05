import asyncio

import pytest

import app


class _DummyResponse:
  def __init__(self, payload):
    self._payload = payload

  def raise_for_status(self):
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


def test_coverage_timeout_maps_to_504(monkeypatch):
  monkeypatch.setattr(app, "COVERAGE_API_URL", "https://coverage.example.com")
  timeout_exc = app.httpx.TimeoutException("timeout")
  dummy = _DummyClient(exc=timeout_exc)
  monkeypatch.setattr(app.httpx, "AsyncClient", lambda timeout: dummy)

  with pytest.raises(app.HTTPException) as exc:
    asyncio.run(app.get_coverage())
  assert exc.value.status_code == 504
  assert exc.value.detail == "coverage_api_timeout"
