import app


def _reset_presence_state():
  app.seen_devices.clear()
  app.mqtt_seen.clear()
  app.mqtt_online_source.clear()
  app.mqtt_status_seen.clear()
  app.mqtt_status_values.clear()
  app.mqtt_internal_seen.clear()
  app.mqtt_packets_seen.clear()
  app.last_seen_broadcast.clear()


def test_parse_meshcore_topic_extracts_iata_node_and_kind():
  iata, node_id, kind = app._parse_meshcore_topic("meshcore/BOS/ABC123/status")
  assert iata == "BOS"
  assert node_id == "ABC123"
  assert kind == "status"

  iata, node_id, kind = app._parse_meshcore_topic("meshcore/BOS/ABC123")
  assert iata is None
  assert node_id is None
  assert kind is None


def test_select_mqtt_online_source_prefers_internal(monkeypatch):
  _reset_presence_state()
  monkeypatch.setattr(app, "MQTT_ONLINE_STATUS_TTL_SECONDS", 300)
  monkeypatch.setattr(app, "MQTT_ONLINE_INTERNAL_TTL_SECONDS", 300)
  monkeypatch.setattr(app, "MQTT_STATUS_OFFLINE_VALUES_SET", {"offline"})

  now = 1000.0
  app.mqtt_status_seen["NODE"] = now - 10
  app.mqtt_status_values["NODE"] = "online"
  app.mqtt_internal_seen["NODE"] = now - 2

  source, ts = app._select_mqtt_online_source("NODE", now)
  assert source == "internal"
  assert ts == now - 2


def test_record_mqtt_presence_online_then_explicit_offline(monkeypatch):
  _reset_presence_state()
  monkeypatch.setattr(app, "MQTT_ONLINE_STATUS_TTL_SECONDS", 300)
  monkeypatch.setattr(app, "MQTT_ONLINE_INTERNAL_TTL_SECONDS", 300)
  monkeypatch.setattr(app, "MQTT_STATUS_OFFLINE_VALUES_SET", {"offline", "disconnected"})

  event_online = app._record_mqtt_presence(
    "meshcore/BOS/NODE/status", b'{"status":"online"}', 1000.0
  )
  assert event_online is not None
  assert event_online["presence_transition"] == "online"
  assert event_online["mqtt_online_source"] == "status"
  assert app.mqtt_seen["NODE"] == 1000.0

  event_internal = app._record_mqtt_presence(
    "meshcore/BOS/NODE/internal", b'{"timestamp":1772678122721}', 1005.0
  )
  assert event_internal is not None
  assert event_internal["presence_transition"] == "stable"
  assert event_internal["mqtt_online_source"] == "internal"
  assert app.mqtt_seen["NODE"] == 1005.0

  event_offline = app._record_mqtt_presence(
    "meshcore/BOS/NODE/status", b'{"status":"offline"}', 1010.0
  )
  assert event_offline is not None
  assert event_offline["presence_transition"] == "offline"
  assert event_offline["mqtt_seen_ts"] is None
  assert "NODE" not in app.mqtt_seen


def test_mqtt_presence_summary_counts_off_map_online_and_feeding(monkeypatch):
  _reset_presence_state()
  monkeypatch.setattr(app, "MQTT_ONLINE_STATUS_TTL_SECONDS", 300)
  monkeypatch.setattr(app, "MQTT_ONLINE_INTERNAL_TTL_SECONDS", 300)
  monkeypatch.setattr(app, "MQTT_ACTIVITY_PACKETS_TTL_SECONDS", 300)

  # No mapped device entries: these are off-map MQTT clients.
  app._record_mqtt_presence("meshcore/BOS/NODEA/status", b'{"status":"online"}', 1000.0)
  app._record_mqtt_presence("meshcore/BOS/NODEB/internal", b'{"timestamp":1}', 1000.0)
  app._record_mqtt_presence("meshcore/BOS/NODEB/packets", b'{"hash":"1"}', 1000.0)

  summary = app._mqtt_presence_summary(1010.0)
  assert summary["connected_total"] == 2
  assert summary["connected_on_map"] == 0
  assert summary["connected_off_map"] == 2
  assert summary["feeding_total"] == 1
  assert summary["feeding_on_map"] == 0
  assert summary["feeding_off_map"] == 1
