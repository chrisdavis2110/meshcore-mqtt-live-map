import asyncio
import json

from starlette.websockets import WebSocketDisconnect

import app


class DummyWebSocket:
  def __init__(self):
    self.query_params = {}
    self.headers = {}
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
