import time

import app
import decoder
import history
import state
from fastapi.testclient import TestClient


class _MutationGuardDict(dict):
  """Behaves like a dict but rejects direct live-view iteration."""

  def __iter__(self):
    raise RuntimeError("dictionary changed size during iteration")

  def items(self):
    raise RuntimeError("dictionary changed size during iteration")

  def keys(self):
    raise RuntimeError("dictionary changed size during iteration")

  def values(self):
    raise RuntimeError("dictionary changed size during iteration")

  def copy(self):
    return dict(dict.items(self))


class _DummyLoop:
  def call_soon_threadsafe(self, fn, *args, **kwargs):
    fn(*args, **kwargs)


class _DummyMsg:
  topic = "meshcore/TEST/NODE/status"
  payload = b'{}'


class _DeadThread:
  def is_alive(self):
    return False


class _ConnectedClientWithDeadThread:
  _thread = _DeadThread()

  def is_connected(self):
    return True


class _AliveThread:
  def is_alive(self):
    return True


class _ConnectedClient:
  _thread = _AliveThread()

  def is_connected(self):
    return True


class _DoneTask:
  def done(self):
    return True


def test_presence_summary_uses_stable_dictionary_snapshots(monkeypatch):
  now = 1000.0
  device = state.DeviceState("NODE", 42.0, -71.0, now)
  monkeypatch.setattr(app, "devices", _MutationGuardDict({"NODE": device}))
  monkeypatch.setattr(app, "mqtt_seen", _MutationGuardDict({"NODE": now}))
  monkeypatch.setattr(
    app, "mqtt_online_source", _MutationGuardDict({"NODE": "status"})
  )
  monkeypatch.setattr(app, "mqtt_status_seen", _MutationGuardDict({"NODE": now}))
  monkeypatch.setattr(
    app, "mqtt_status_values", _MutationGuardDict({"NODE": "online"})
  )
  monkeypatch.setattr(app, "mqtt_internal_seen", _MutationGuardDict())
  monkeypatch.setattr(app, "mqtt_packets_seen", _MutationGuardDict({"NODE": now}))

  summary = app._mqtt_presence_summary(now)

  assert summary == {
    "connected_total": 1,
    "connected_on_map": 1,
    "connected_off_map": 0,
    "feeding_total": 1,
    "feeding_on_map": 1,
    "feeding_off_map": 0,
  }


def test_serialized_state_is_detached_from_live_mutable_state(monkeypatch):
  now = time.time()
  device = state.DeviceState("NODE", 42.0, -71.0, now)
  guarded_devices = _MutationGuardDict({"NODE": device})
  guarded_trails = _MutationGuardDict({"NODE": [[42.0, -71.0, now]]})
  monkeypatch.setattr(app, "devices", guarded_devices)
  monkeypatch.setattr(app, "trails", guarded_trails)

  payload = app._serialize_state()
  guarded_devices["OTHER"] = state.DeviceState("OTHER", 43.0, -72.0, now)
  guarded_trails["NODE"].append([44.0, -73.0, now])

  assert set(payload["devices"]) == {"NODE"}
  assert len(payload["trails"]["NODE"]) == 1


def test_mqtt_callback_logs_failure_and_processes_next_message(
  monkeypatch, caplog
):
  attempts = 0

  def _record_presence(*_args, **_kwargs):
    nonlocal attempts
    attempts += 1
    if attempts == 1:
      raise RuntimeError("injected callback failure")
    return None

  monkeypatch.setattr(app, "_record_mqtt_presence", _record_presence)
  monkeypatch.setattr(app, "_try_parse_payload", lambda *_args: (None, {}))
  app.stats.pop("callback_errors_total", None)
  app.stats.pop("last_callback_error_ts", None)

  app.mqtt_on_message(None, {"loop": _DummyLoop()}, _DummyMsg())
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, _DummyMsg())

  assert attempts == 2
  assert app.stats["callback_errors_total"] == 1
  assert app.stats["last_callback_error_ts"] is not None
  assert "injected callback failure" in caplog.text


def test_mqtt_health_detects_dead_network_thread(monkeypatch):
  monkeypatch.setattr(app, "mqtt_client", _ConnectedClientWithDeadThread())

  health = app._mqtt_listener_health()

  assert health["status"] == "unhealthy"
  assert health["connected"] is True
  assert health["network_loop_alive"] is False


def test_health_endpoint_fails_when_mqtt_network_thread_is_dead(monkeypatch):
  monkeypatch.setattr(app, "mqtt_client", _ConnectedClientWithDeadThread())

  response = TestClient(app.app).get("/health")

  assert response.status_code == 503
  assert response.json()["mqtt"]["status"] == "unhealthy"


def test_health_endpoint_fails_when_broadcaster_task_stops(monkeypatch):
  monkeypatch.setattr(app, "mqtt_client", _ConnectedClient())
  monkeypatch.setattr(app, "broadcaster_task", _DoneTask())

  response = TestClient(app.app).get("/health")

  assert response.status_code == 503
  assert response.json()["broadcaster"]["status"] == "unhealthy"


def test_snapshot_helpers_use_stable_shared_state_copies(monkeypatch):
  now = time.time()
  device = state.DeviceState("NODE", 42.0, -71.0, now)
  guarded_trails = _MutationGuardDict({"NODE": [[42.0, -71.0, now]]})
  monkeypatch.setattr(app, "BLOCKED_NAME_SYMBOL_FILTER_ENABLED", False)
  monkeypatch.setattr(app, "devices", _MutationGuardDict({"NODE": device}))
  monkeypatch.setattr(app, "trails", guarded_trails)
  monkeypatch.setattr(
    app,
    "routes",
    _MutationGuardDict({
      "route": {
        "id": "route",
        "expires_at": now + 120,
        "points": [],
      }
    }),
  )

  device_payloads = app._visible_device_payloads()
  trail_payloads = app._visible_trails()
  route_payloads = app._snapshot_routes(now)
  guarded_trails["NODE"].append([43.0, -72.0, now])

  assert set(device_payloads) == {"NODE"}
  assert len(trail_payloads["NODE"]) == 1
  assert [route["id"] for route in route_payloads] == ["route"]


def test_stats_endpoint_uses_stable_shared_state_copies(monkeypatch):
  now = time.time()
  monkeypatch.setattr(app, "PROD_MODE", False)
  monkeypatch.setattr(app, "seen_devices", _MutationGuardDict({"NODE": now}))
  monkeypatch.setattr(
    app, "topic_counts", _MutationGuardDict({"meshcore/TEST/NODE/status": 1})
  )

  response = TestClient(app.app).get("/stats")

  assert response.status_code == 200
  assert response.json()["seen_recent"][0][0] == "NODE"


def test_decoder_hash_rebuild_snapshots_device_ids(monkeypatch):
  device = state.DeviceState("ABCDEF12", 42.0, -71.0, time.time())
  monkeypatch.setattr(
    decoder, "devices", _MutationGuardDict({"ABCDEF12": device})
  )

  decoder._rebuild_node_hash_map()

  assert decoder.node_hash_to_device["AB"] == "ABCDEF12"


def test_peer_history_prune_snapshots_pairs_and_buckets(monkeypatch):
  now = time.time()
  bucket_start = history._peer_history_bucket_start(now)
  pairs = _MutationGuardDict({
    "A|B": {
      "a_id": "A",
      "b_id": "B",
      "buckets": _MutationGuardDict({str(bucket_start): 1}),
      "last_ts": now,
    }
  })
  monkeypatch.setattr(state, "peer_history_pairs", pairs)

  changed = history._prune_peer_history(now)

  assert changed is False
  assert pairs["A|B"]["buckets"] == {str(bucket_start): 1}
