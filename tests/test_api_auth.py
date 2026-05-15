from starlette.requests import Request

import pytest
from fastapi.testclient import TestClient

import app


class _DummyWebSocket:
  def __init__(self, query_params=None, headers=None):
    self.query_params = query_params or {}
    self.headers = headers or {}


class _DummyTurnstileVerifier:
  def __init__(self, valid_tokens=None):
    self.valid_tokens = set(valid_tokens or [])

  def verify_auth_token(self, token):
    return token in self.valid_tokens


def _request(path, query="", headers=None):
  headers = headers or {}
  raw_headers = [
    (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()
  ]
  scope = {
    "type": "http",
    "http_version": "1.1",
    "method": "GET",
    "scheme": "http",
    "path": path,
    "raw_path": path.encode("latin-1"),
    "query_string": query.encode("latin-1"),
    "headers": raw_headers,
    "client": ("127.0.0.1", 12345),
    "server": ("testserver", 80),
    "root_path": "",
  }
  return Request(scope)


def test_prod_mode_requires_token_for_snapshot_api_nodes_and_peers(monkeypatch):
  monkeypatch.setattr(app, "PROD_MODE", True)
  monkeypatch.setattr(app, "PROD_TOKEN", "secret-token")

  # snapshot without token should fail
  req_no_token = _request("/snapshot")
  with pytest.raises(app.HTTPException) as exc:
    app.snapshot(req_no_token)
  assert exc.value.status_code == 401

  # snapshot with query token should pass
  req_query_token = _request("/snapshot", query="token=secret-token")
  snap = app.snapshot(req_query_token)
  assert "devices" in snap

  # /api/nodes with bearer token should pass
  req_bearer = _request(
    "/api/nodes", headers={"authorization": "Bearer secret-token"}
  )
  nodes = app.api_nodes(req_bearer)
  assert "data" in nodes

  # /peers without token should fail, with x-token should pass
  with pytest.raises(app.HTTPException) as exc:
    app.get_peers("dummy-device", _request("/peers/dummy-device"))
  assert exc.value.status_code == 401

  req_x_token = _request("/peers/dummy-device", headers={"x-token": "secret-token"})
  peers = app.get_peers("dummy-device", req_x_token, limit=5)
  assert peers["device_id"] == "dummy-device"


def test_non_prod_mode_does_not_require_token(monkeypatch):
  monkeypatch.setattr(app, "PROD_MODE", False)
  monkeypatch.setattr(app, "PROD_TOKEN", "ignored")

  snap = app.snapshot(_request("/snapshot"))
  nodes = app.api_nodes(_request("/api/nodes"))
  peers = app.get_peers("dummy-device", _request("/peers/dummy-device"), limit=3)

  assert isinstance(snap, dict)
  assert "data" in nodes
  assert peers["device_id"] == "dummy-device"


def test_snapshot_omits_history_when_route_history_disabled(monkeypatch):
  monkeypatch.setattr(app, "PROD_MODE", False)
  monkeypatch.setattr(app, "ROUTE_HISTORY_ENABLED", False)
  monkeypatch.setattr(app, "ROUTE_HISTORY_HOURS", 24)
  app.route_history_edges.clear()
  app.route_history_edges["edge-1"] = {
    "id": "edge-1",
    "a": [1.0, 2.0],
    "b": [3.0, 4.0],
    "count": 5,
    "recent": [],
    "last_ts": 1000.0,
  }

  snap = app.snapshot(_request("/snapshot"))

  assert snap["history_edges"] == []
  assert snap["history_window_seconds"] == 0

  app.route_history_edges.clear()


def test_qr_endpoint_requires_prod_token(monkeypatch):
  monkeypatch.setattr(app, "PROD_MODE", True)
  monkeypatch.setattr(app, "PROD_TOKEN", "secret-token")

  client = TestClient(app.app)

  unauthorized = client.get("/qr", params={"text": "mesh://ABC123"})
  assert unauthorized.status_code == 401

  authorized = client.get(
    "/qr",
    params={"text": "mesh://ABC123", "token": "secret-token"},
  )
  assert authorized.status_code == 200
  assert authorized.headers["content-type"].startswith("image/png")
  assert authorized.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_qr_endpoint_builds_meshcore_contact_uri(monkeypatch):
  monkeypatch.setattr(app, "PROD_MODE", False)
  captured = {}

  class _FakeImage:
    def convert(self, _mode):
      return self

    def save(self, buffer, format="PNG"):
      captured["format"] = format
      buffer.write(b"fake-png")

  class _FakeQRCode:
    def __init__(self, **kwargs):
      captured["kwargs"] = kwargs

    def add_data(self, value):
      captured["value"] = value

    def make(self, fit=True):
      captured["fit"] = fit

    def make_image(self, fill_color="black", back_color="white"):
      captured["fill_color"] = fill_color
      captured["back_color"] = back_color
      return _FakeImage()

  monkeypatch.setattr(app.qrcode, "QRCode", _FakeQRCode)
  response = app.qr_code(
    _request("/qr"),
    name="Test Node",
    public_key="A1" * 32,
    device_type=2,
    box_size=14,
    border=4,
  )

  assert captured["value"] == (
    "meshcore://contact/add?"
    "name=Test+Node&public_key="
    "a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1"
    "a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1"
    "&type=2"
  )
  assert captured["kwargs"]["error_correction"] == app.qrcode.constants.ERROR_CORRECT_M
  assert captured["kwargs"]["box_size"] == 14
  assert captured["kwargs"]["border"] == 4
  assert response.body == b"fake-png"


def test_prod_route_payload_keeps_hop_hashes_for_ui(monkeypatch):
  monkeypatch.setattr(app, "PROD_MODE", True)
  payload = app._route_payload(
    {
      "id": "route-1",
      "points": [[42.0, -71.0], [42.1, -71.1], [42.2, -71.2]],
      "hashes": ["AB", "BC"],
      "point_ids": ["AA1111", "BB2222", "CC3333"],
      "origin_id": "AA1111",
      "receiver_id": "CC3333",
      "route_mode": "path",
      "ts": 1.0,
      "expires_at": 2.0,
      "payload_type": 5,
      "message_hash": "7232623D62E7848D",
      "sender_name": "yellowcooln",
    }
  )

  assert payload["hashes"] == ["AB", "BC"]
  assert payload["point_ids"] == ["AA1111", "BB2222", "CC3333"]
  assert payload["origin_id"] == "AA1111"
  assert payload["receiver_id"] == "CC3333"
  assert payload["message_hash"] == "7232623D62E7848D"
  assert payload["sender_name"] == "yellowcooln"


def test_ws_authorized_in_prod_mode_accepts_query_and_header_tokens(monkeypatch):
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)
  monkeypatch.setattr(app, "turnstile_verifier", None)
  monkeypatch.setattr(app, "PROD_MODE", True)
  monkeypatch.setattr(app, "PROD_TOKEN", "secret-token")

  assert app._ws_authorized(
    _DummyWebSocket(query_params={"token": "secret-token"})
  ) is True
  assert app._ws_authorized(
    _DummyWebSocket(query_params={"access_token": "secret-token"})
  ) is True
  assert app._ws_authorized(
    _DummyWebSocket(headers={"authorization": "Bearer secret-token"})
  ) is True
  assert app._ws_authorized(
    _DummyWebSocket(headers={"x-token": "secret-token"})
  ) is True
  assert app._ws_authorized(
    _DummyWebSocket(query_params={"token": "wrong-token"})
  ) is False


def test_ws_authorized_allows_turnstile_auth_token(monkeypatch):
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", True)
  monkeypatch.setattr(
    app,
    "turnstile_verifier",
    _DummyTurnstileVerifier(valid_tokens={"good-auth-token"}),
  )
  monkeypatch.setattr(app, "PROD_MODE", True)
  monkeypatch.setattr(app, "PROD_TOKEN", "secret-token")

  cookie_ws = _DummyWebSocket(headers={"cookie": "meshmap_auth=good-auth-token"})
  assert app._ws_authorized(cookie_ws) is True

  query_ws = _DummyWebSocket(query_params={"auth": "good-auth-token"})
  assert app._ws_authorized(query_ws) is True

  header_ws = _DummyWebSocket(headers={"authorization": "Bearer good-auth-token"})
  assert app._ws_authorized(header_ws) is True

  bad_ws = _DummyWebSocket(headers={"cookie": "meshmap_auth=bad-token"})
  assert app._ws_authorized(bad_ws) is False
