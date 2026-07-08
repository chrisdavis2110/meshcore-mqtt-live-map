import app


def _device(device_id, name):
  return app.DeviceState(
    device_id=device_id,
    lat=42.0,
    lon=-71.0,
    ts=1000.0,
    name=name,
  )


def test_blocked_name_symbol_filter_hides_devices_trails_and_routes(monkeypatch):
  monkeypatch.setattr(app, "BLOCKED_NAME_SYMBOL_FILTER_ENABLED", True)
  app.devices.clear()
  app.device_names.clear()
  app.trails.clear()
  app.routes.clear()
  try:
    app.devices["ok"] = _device("ok", "normal node")
    app.devices["blocked"] = _device("blocked", "bad 🛑 node")
    app.trails["ok"] = [[42.0, -71.0, 1000.0]]
    app.trails["blocked"] = [[43.0, -72.0, 1000.0]]
    app.routes["keep"] = {
      "id": "keep",
      "point_ids": ["ok"],
      "points": [[42.0, -71.0], [42.1, -71.1]],
      "expires_at": 2000.0,
    }
    app.routes["drop"] = {
      "id": "drop",
      "point_ids": ["ok", "blocked"],
      "points": [[42.0, -71.0], [43.0, -72.0]],
      "expires_at": 2000.0,
    }

    assert set(app._visible_device_payloads()) == {"ok"}
    assert set(app._visible_trails()) == {"ok"}
    assert [route["id"] for route in app._snapshot_routes(now=1000.0)] == ["keep"]
  finally:
    app.devices.clear()
    app.device_names.clear()
    app.trails.clear()
    app.routes.clear()


def test_blocked_name_symbol_filter_ignores_symbols_when_disabled(monkeypatch):
  monkeypatch.setattr(app, "BLOCKED_NAME_SYMBOL_FILTER_ENABLED", False)
  app.devices.clear()
  app.trails.clear()
  app.routes.clear()
  try:
    app.devices["blocked"] = _device("blocked", "bad 🚫 node")
    app.trails["blocked"] = [[43.0, -72.0, 1000.0]]
    app.routes["visible"] = {
      "id": "visible",
      "point_ids": ["blocked"],
      "points": [[43.0, -72.0], [43.1, -72.1]],
      "expires_at": 2000.0,
    }

    assert set(app._visible_device_payloads()) == {"blocked"}
    assert set(app._visible_trails()) == {"blocked"}
    assert [route["id"] for route in app._snapshot_routes(now=1000.0)] == ["visible"]
  finally:
    app.devices.clear()
    app.trails.clear()
    app.routes.clear()


def test_blocked_name_symbol_filter_hides_sender_name_routes(monkeypatch):
  monkeypatch.setattr(app, "BLOCKED_NAME_SYMBOL_FILTER_ENABLED", True)
  app.routes.clear()
  try:
    app.routes["drop"] = {
      "id": "drop",
      "sender_name": "nope ⛔ node",
      "points": [[42.0, -71.0], [42.1, -71.1]],
      "expires_at": 2000.0,
    }

    assert app._snapshot_routes(now=1000.0) == []
  finally:
    app.routes.clear()
