import json
import time

import app
import history
import state


def _clear_peer_state():
  state.route_history_segments.clear()
  state.route_history_edges.clear()
  state.peer_history_pairs.clear()


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
