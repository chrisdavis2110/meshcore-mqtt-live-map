import json
import time

import app
import history
import state


def _clear_peer_state():
  state.route_history_segments.clear()
  state.route_history_edges.clear()
  state.peer_history_pairs.clear()
  state.devices.clear()
  state.device_names.clear()
  state.device_roles.clear()


def _route(ts):
  return {
    "points": [[42.3601, -71.0589], [42.3611, -71.0579]],
    "point_ids": ["AA001111", "BB001111"],
    "payload_type": 5,
    "message_hash": f"msg-{int(ts)}",
    "origin_id": "AA001111",
    "receiver_id": "BB001111",
    "route_mode": "path",
    "topic": "meshcore/test",
    "ts": ts,
  }


def test_peer_stats_use_bucket_history_even_when_segment_limit_prunes(monkeypatch):
  _clear_peer_state()
  now = time.time()

  monkeypatch.setattr(history, "ROUTE_HISTORY_ENABLED", True)
  monkeypatch.setattr(history, "ROUTE_HISTORY_HOURS", 24)
  monkeypatch.setattr(history, "ROUTE_HISTORY_MAX_SEGMENTS", 2)
  monkeypatch.setattr(history, "ROUTE_HISTORY_ALLOWED_MODES_SET", {"path"})
  monkeypatch.setattr(app, "ROUTE_HISTORY_HOURS", 24)

  history._record_route_history(_route(now - 3 * 3600))
  history._record_route_history(_route(now - 2 * 3600))
  history._record_route_history(_route(now - 1 * 3600))

  assert len(state.route_history_segments) == 2

  outbound = app._peer_stats_for_device("AA001111", limit=8)
  inbound = app._peer_stats_for_device("BB001111", limit=8)

  assert outbound["outgoing_total"] == 3
  assert inbound["incoming_total"] == 3
  assert outbound["outgoing"][0]["peer_id"] == "BB001111"
  assert inbound["incoming"][0]["peer_id"] == "AA001111"


def test_state_round_trip_preserves_peer_history_buckets(tmp_path, monkeypatch):
  _clear_peer_state()
  now = time.time()
  state_file = tmp_path / "state.json"

  monkeypatch.setattr(history, "ROUTE_HISTORY_ENABLED", True)
  monkeypatch.setattr(history, "ROUTE_HISTORY_HOURS", 24)
  monkeypatch.setattr(history, "ROUTE_HISTORY_MAX_SEGMENTS", 10)
  monkeypatch.setattr(history, "ROUTE_HISTORY_ALLOWED_MODES_SET", {"path"})
  monkeypatch.setattr(app, "ROUTE_HISTORY_HOURS", 24)
  monkeypatch.setattr(app, "STATE_FILE", str(state_file))
  monkeypatch.setattr(app, "DEVICE_ROLES_FILE", "")
  monkeypatch.setattr(app, "DEVICE_COORDS_FILE", "")

  history._record_route_history(_route(now - 600))
  history._record_route_history(_route(now - 300))

  state_file.write_text(json.dumps(app._serialize_state()), encoding="utf-8")

  _clear_peer_state()
  app._load_state()

  assert len(state.peer_history_pairs) == 1

  outbound = app._peer_stats_for_device("AA001111", limit=8)
  assert outbound["outgoing_total"] == 2
  assert outbound["outgoing"][0]["peer_id"] == "BB001111"


def test_peer_history_records_route_ids_without_drawn_segments(monkeypatch):
  _clear_peer_state()
  now = time.time()

  monkeypatch.setattr(history, "ROUTE_HISTORY_ENABLED", True)
  monkeypatch.setattr(history, "ROUTE_HISTORY_HOURS", 24)
  monkeypatch.setattr(history, "ROUTE_HISTORY_MAX_SEGMENTS", 10)
  monkeypatch.setattr(history, "ROUTE_HISTORY_ALLOWED_MODES_SET", {"path"})
  monkeypatch.setattr(app, "ROUTE_HISTORY_HOURS", 24)

  history._record_route_history(
    {
      "points": [[0.0, 0.0], [0.0, 0.0]],
      "point_ids": ["AA001111", "BB001111"],
      "payload_type": 5,
      "message_hash": "msg-undrawn",
      "origin_id": "AA001111",
      "receiver_id": "BB001111",
      "route_mode": "path",
      "topic": "meshcore/test",
      "ts": now,
    }
  )

  assert len(state.route_history_segments) == 0
  outbound = app._peer_stats_for_device("AA001111", limit=8)
  inbound = app._peer_stats_for_device("BB001111", limit=8)

  assert outbound["outgoing_total"] == 1
  assert inbound["incoming_total"] == 1
  assert outbound["outgoing"][0]["peer_id"] == "BB001111"
  assert inbound["incoming"][0]["peer_id"] == "AA001111"


def test_peer_history_still_records_when_route_history_disabled(monkeypatch):
  _clear_peer_state()
  now = time.time()

  monkeypatch.setattr(history, "ROUTE_HISTORY_ENABLED", False)
  monkeypatch.setattr(history, "ROUTE_HISTORY_HOURS", 24)
  monkeypatch.setattr(history, "ROUTE_HISTORY_ALLOWED_MODES_SET", {"path"})
  monkeypatch.setattr(app, "ROUTE_HISTORY_HOURS", 24)

  history._record_route_history(_route(now))

  assert len(state.route_history_segments) == 0
  outbound = app._peer_stats_for_device("AA001111", limit=8)
  inbound = app._peer_stats_for_device("BB001111", limit=8)

  assert outbound["outgoing_total"] == 1
  assert inbound["incoming_total"] == 1
  assert outbound["outgoing"][0]["peer_id"] == "BB001111"
  assert inbound["incoming"][0]["peer_id"] == "AA001111"


def test_route_history_tracks_path_hash_byte_counts(monkeypatch):
  _clear_peer_state()
  now = time.time()

  monkeypatch.setattr(history, "ROUTE_HISTORY_ENABLED", True)
  monkeypatch.setattr(history, "ROUTE_HISTORY_HOURS", 24)
  monkeypatch.setattr(history, "ROUTE_HISTORY_MAX_SEGMENTS", 10)
  monkeypatch.setattr(history, "ROUTE_HISTORY_ALLOWED_MODES_SET", {"path"})

  route = _route(now)
  route["hashes"] = ["aa", "bbbb", "cccccc"]
  history._record_route_history(route)

  assert len(state.route_history_edges) == 1
  edge = next(iter(state.route_history_edges.values()))
  assert edge["byte_counts"] == {"1": 1, "2": 1, "3": 1}
  assert edge["recent"][0]["route_byte_widths"] == [1, 2, 3]


def test_peer_stats_report_unique_counts_before_limit(monkeypatch):
  _clear_peer_state()
  now = time.time()
  bucket = history._peer_history_bucket_start(now)

  monkeypatch.setattr(app, "ROUTE_HISTORY_HOURS", 24)
  state.peer_history_pairs["AA001111:BB001111"] = {
    "a_id": "AA001111",
    "b_id": "BB001111",
    "buckets": {str(bucket): 2},
  }
  state.peer_history_pairs["AA001111:CC001111"] = {
    "a_id": "AA001111",
    "b_id": "CC001111",
    "buckets": {str(bucket): 1},
  }

  payload = app._peer_stats_for_device("AA001111", limit=1)

  assert payload["outgoing_unique"] == 2
  assert payload["outgoing_total"] == 3
  assert len(payload["outgoing"]) == 1


def test_get_peers_adds_distance_m_for_located_peers(monkeypatch):
  _clear_peer_state()
  now = time.time()
  bucket = history._peer_history_bucket_start(now)

  monkeypatch.setattr(app, "PROD_MODE", False)
  monkeypatch.setattr(app, "ROUTE_HISTORY_HOURS", 24)
  state.devices["AA001111"] = state.DeviceState(
    device_id="AA001111",
    lat=42.3601,
    lon=-71.0589,
    ts=now,
    name="Origin",
    role="repeater",
  )
  state.devices["BB001111"] = state.DeviceState(
    device_id="BB001111",
    lat=42.3611,
    lon=-71.0579,
    ts=now,
    name="Peer",
    role="repeater",
  )
  state.peer_history_pairs["AA001111:BB001111"] = {
    "a_id": "AA001111",
    "b_id": "BB001111",
    "buckets": {str(bucket): 3},
  }

  payload = app.get_peers("AA001111", None, limit=8)
  peer = payload["outgoing"][0]
  expected = app._haversine_m(42.3601, -71.0589, 42.3611, -71.0579)

  assert payload["lat"] == 42.3601
  assert payload["lon"] == -71.0589
  assert peer["peer_id"] == "BB001111"
  assert peer["distance_m"] == round(expected, 2)
