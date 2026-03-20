import asyncio
import json
import time

from starlette.websockets import WebSocketDisconnect

import app


class DummyWebSocket:
  def __init__(self, query_params=None, headers=None):
    self.query_params = query_params or {}
    self.headers = headers or {}
    self.accepted = False
    self.closed_code = None
    self.sent_messages = []

  async def accept(self):
    self.accepted = True

  async def close(self, code=1000):
    self.closed_code = code

  async def send_text(self, text):
    self.sent_messages.append(text)

  async def receive_text(self):
    raise WebSocketDisconnect()


def test_ws_endpoint_sends_snapshot_payload(monkeypatch):
  ws = DummyWebSocket()
  app.clients.clear()
  monkeypatch.setattr(app, "PROD_MODE", False)

  asyncio.run(app.ws_endpoint(ws))

  assert ws.accepted is True
  assert ws.closed_code is None
  assert len(ws.sent_messages) >= 1

  payload = json.loads(ws.sent_messages[0])
  assert payload["type"] == "snapshot"
  assert "devices" in payload
  assert "routes" in payload
  assert ws not in app.clients


def test_ws_endpoint_rejects_unauthorized_in_prod_mode(monkeypatch):
  ws = DummyWebSocket()
  app.clients.clear()
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)
  monkeypatch.setattr(app, "turnstile_verifier", None)
  monkeypatch.setattr(app, "PROD_MODE", True)
  monkeypatch.setattr(app, "PROD_TOKEN", "secret-token")

  asyncio.run(app.ws_endpoint(ws))

  assert ws.accepted is True
  assert ws.closed_code == 1008
  assert ws.sent_messages == []
  assert ws not in app.clients


def test_ws_endpoint_accepts_query_token_in_prod_mode(monkeypatch):
  ws = DummyWebSocket(query_params={"token": "secret-token"})
  app.clients.clear()
  monkeypatch.setattr(app, "TURNSTILE_ENABLED", False)
  monkeypatch.setattr(app, "turnstile_verifier", None)
  monkeypatch.setattr(app, "PROD_MODE", True)
  monkeypatch.setattr(app, "PROD_TOKEN", "secret-token")

  asyncio.run(app.ws_endpoint(ws))

  assert ws.accepted is True
  assert ws.closed_code is None
  assert len(ws.sent_messages) >= 1


def test_ws_snapshot_omits_near_expired_routes_and_includes_server_time(monkeypatch):
  ws = DummyWebSocket()
  app.clients.clear()
  app.routes.clear()
  monkeypatch.setattr(app, "PROD_MODE", False)
  now = 1000.0
  monkeypatch.setattr(app.time, "time", lambda: now)
  app.routes["keep"] = {
    "id": "keep",
    "points": [[1.0, 2.0], [3.0, 4.0]],
    "expires_at": now + 30.0,
  }
  app.routes["drop"] = {
    "id": "drop",
    "points": [[1.0, 2.0], [3.0, 4.0]],
    "expires_at": now + 2.0,
  }

  asyncio.run(app.ws_endpoint(ws))

  payload = json.loads(ws.sent_messages[0])
  route_ids = [route.get("id") for route in payload.get("routes", [])]
  assert "keep" in route_ids
  assert "drop" not in route_ids
  assert payload.get("server_time") == now
  app.routes.clear()
