from datetime import datetime, timezone

from starlette.requests import Request

import app
import state


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


def _clear_state():
  state.devices.clear()
  state.seen_devices.clear()


def _add_device(device_id, lat, lon, ts):
  state.devices[device_id] = state.DeviceState(
    device_id=device_id,
    lat=lat,
    lon=lon,
    ts=ts,
    role="repeater",
  )
  state.seen_devices[device_id] = ts


def test_api_nodes_default_format_and_nested_mode(monkeypatch):
  _clear_state()
  try:
    monkeypatch.setattr(app, "PROD_MODE", False)
    _add_device("AA001111", 42.0, -71.0, 1000.0)
    req = _request("/api/nodes")

    payload = app.api_nodes(req)
    assert isinstance(payload["data"], list)
    assert isinstance(payload["nodes"], list)
    assert len(payload["data"]) == 1

    nested = app.api_nodes(req, format="nested")
    assert isinstance(nested["data"], dict)
    assert isinstance(nested["data"]["nodes"], list)
    assert "nodes" not in nested
  finally:
    _clear_state()


def test_api_nodes_updated_since_and_full_mode_override(monkeypatch):
  _clear_state()
  try:
    monkeypatch.setattr(app, "PROD_MODE", False)
    _add_device("OLD11111", 42.0, -71.0, 1000.0)
    _add_device("NEW11111", 42.1, -71.1, 2000.0)
    req = _request("/api/nodes")

    cutoff_iso = datetime.fromtimestamp(
      1500.0, tz=timezone.utc
    ).isoformat().replace("+00:00", "Z")

    filtered = app.api_nodes(req, updated_since=cutoff_iso)
    keys = [item["public_key"] for item in filtered["data"]]
    assert keys == ["NEW11111"]
    assert filtered["updated_since_applied"] is True
    assert filtered["updated_since_ignored"] is False

    full = app.api_nodes(req, updated_since=cutoff_iso, mode="full")
    full_keys = sorted(item["public_key"] for item in full["data"])
    assert full_keys == ["NEW11111", "OLD11111"]
    assert full["updated_since_applied"] is False
    assert full["updated_since_ignored"] is True
  finally:
    _clear_state()
