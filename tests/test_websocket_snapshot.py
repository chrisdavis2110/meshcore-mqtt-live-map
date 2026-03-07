import asyncio
import json

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
