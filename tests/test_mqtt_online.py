import time

import app
import decoder
import state


class _DummyLoop:
  def call_soon_threadsafe(self, fn, *args, **kwargs):
    fn(*args, **kwargs)


class _DummyQueue:
  def __init__(self):
    self.events = []

  def put_nowait(self, event):
    self.events.append(event)


class _DummyMsg:
  def __init__(self, topic, payload=b"{}"):
    self.topic = topic
    self.payload = payload


def _clear_runtime_state():
  app.devices.clear()
  app.seen_devices.clear()
  app.mqtt_seen.clear()
  app.mqtt_online_source.clear()
  app.mqtt_status_seen.clear()
  app.mqtt_status_values.clear()
  app.mqtt_internal_seen.clear()
  app.mqtt_packets_seen.clear()
  app.last_seen_broadcast.clear()
  app.device_names.clear()
  app.device_roles.clear()
  app.device_role_sources.clear()
  app.topic_counts.clear()
  app.routes.clear()
  app.message_origins.clear()
  app.last_seen_in_advert.clear()


def test_mqtt_status_topic_marks_device_online_without_coords(monkeypatch):
  _clear_runtime_state()
  monkeypatch.setattr(decoder, "MQTT_ONLINE_TOPIC_SUFFIXES", ("/status",))
  monkeypatch.setattr(app, "_try_parse_payload", lambda *_args, **_kwargs: (None, {}))

  msg = _DummyMsg("meshcore/BOS/ABCD1111/status")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, msg)

  assert "ABCD1111" in app.seen_devices
  assert "ABCD1111" in app.mqtt_seen


def test_mqtt_packets_topic_does_not_mark_online(monkeypatch):
  _clear_runtime_state()
  monkeypatch.setattr(decoder, "MQTT_ONLINE_TOPIC_SUFFIXES", ("/status",))
  monkeypatch.setattr(app, "_try_parse_payload", lambda *_args, **_kwargs: (None, {}))

  msg = _DummyMsg("meshcore/BOS/ABCD1111/packets")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, msg)

  assert "ABCD1111" not in app.seen_devices
  assert "ABCD1111" not in app.mqtt_seen


def test_existing_device_emits_device_seen_update(monkeypatch):
  _clear_runtime_state()
  monkeypatch.setattr(decoder, "MQTT_ONLINE_TOPIC_SUFFIXES", ("/status",))
  monkeypatch.setattr(app, "_try_parse_payload", lambda *_args, **_kwargs: (None, {}))
  monkeypatch.setattr(app, "MQTT_SEEN_BROADCAST_MIN_SECONDS", 0)
  queue = _DummyQueue()
  monkeypatch.setattr(app, "update_queue", queue)

  app.devices["ABCD1111"] = state.DeviceState(
    device_id="ABCD1111",
    lat=42.36,
    lon=-71.05,
    ts=time.time(),
    role="repeater",
  )

  msg = _DummyMsg("meshcore/BOS/ABCD1111/status")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, msg)

  assert queue.events
  first = queue.events[0]
  assert first["type"] == "device_seen"
  assert first["device_id"] == "ABCD1111"
  assert isinstance(first["mqtt_seen_ts"], float)


def test_device_payload_marks_forced_online_name(monkeypatch):
  _clear_runtime_state()
  monkeypatch.setattr(app, "MQTT_ONLINE_FORCE_NAMES_SET", {"alwaysonline"})
  app.devices["ABCD1111"] = state.DeviceState(
    device_id="ABCD1111",
    lat=42.36,
    lon=-71.05,
    ts=time.time(),
    role="repeater",
    name="AlwaysOnline",
  )

  payload = app._device_payload("ABCD1111", app.devices["ABCD1111"])
  assert payload.get("mqtt_forced") is True


def test_route_event_pads_low_range_two_byte_int_hashes(monkeypatch):
  _clear_runtime_state()
  queue = _DummyQueue()
  monkeypatch.setattr(app, "update_queue", queue)
  monkeypatch.setattr(
    app,
    "_try_parse_payload",
    lambda *_args, **_kwargs: (
      None,
      {
        "result": "decoded_no_location",
        "origin_id": "AA001111",
        "decoder_meta": {
          "payloadType": 8,
          "routeType": 0,
          "messageHash": "deadbeef",
          "pathHashes": [0xAB, 0x1234],
          "pathLength": 2,
        },
      },
    ),
  )

  msg = _DummyMsg("meshcore/BOS/DD001111/packets")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, msg)

  route_events = [event for event in queue.events if event.get("type") == "route"]
  assert route_events
  assert route_events[0]["path_hashes"] == ["00AB", "1234"]


def test_route_event_pads_low_range_three_byte_int_hashes(monkeypatch):
  _clear_runtime_state()
  queue = _DummyQueue()
  monkeypatch.setattr(app, "update_queue", queue)
  monkeypatch.setattr(
    app,
    "_try_parse_payload",
    lambda *_args, **_kwargs: (
      None,
      {
        "result": "decoded_no_location",
        "origin_id": "AA001111",
        "decoder_meta": {
          "payloadType": 8,
          "routeType": 0,
          "messageHash": "feedface",
          "pathHashes": [0xAB, 0x12ABCD],
          "pathLength": 3,
        },
      },
    ),
  )

  msg = _DummyMsg("meshcore/BOS/DD001111/packets")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, msg)

  route_events = [event for event in queue.events if event.get("type") == "route"]
  assert route_events
  assert route_events[0]["path_hashes"] == ["0000AB", "12ABCD"]


def test_route_event_does_not_treat_tx_uploader_as_message_sender_origin(monkeypatch):
  _clear_runtime_state()
  queue = _DummyQueue()
  monkeypatch.setattr(app, "update_queue", queue)

  def _parse(topic, _payload):
    if topic.endswith("/tx/packets"):
      return None, {
        "result": "decoded_no_location",
        "origin_id": "CC001111",
        "direction": "tx",
        "packet_hash": "abc123",
        "decoder_meta": {
          "payloadType": 5,
          "routeType": 0,
          "messageHash": "abc123",
          "path": ["AB"],
        },
      }
    return None, {
      "result": "decoded_no_location",
      "origin_id": "DD009999",
      "direction": "rx",
      "packet_hash": "abc123",
      "decoder_meta": {
        "payloadType": 5,
        "routeType": 0,
        "messageHash": "abc123",
        "path": ["AB"],
      },
    }

  monkeypatch.setattr(app, "_try_parse_payload", _parse)

  tx_msg = _DummyMsg("meshcore/BOS/CC001111/tx/packets")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, tx_msg)

  rx_msg = _DummyMsg("meshcore/BOS/EE002222/packets")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, rx_msg)

  route_events = [event for event in queue.events if event.get("type") == "route"]
  assert len(route_events) >= 2
  assert route_events[-1]["origin_id"] is None
  assert route_events[-1]["receiver_id"] == "EE002222"


def test_route_event_uses_cached_explicit_origin_pubkey(monkeypatch):
  _clear_runtime_state()
  queue = _DummyQueue()
  monkeypatch.setattr(app, "update_queue", queue)

  def _parse(topic, _payload):
    if topic.endswith("/tx/packets"):
      return None, {
        "result": "decoded_no_location",
        "origin_id": "CC001111",
        "direction": "tx",
        "packet_hash": "abc123",
        "decoder_meta": {
          "payloadType": 5,
          "routeType": 0,
          "messageHash": "abc123",
          "location": {
            "pubkey": "E8D10001",
          },
          "path": ["AB"],
        },
      }
    return None, {
      "result": "decoded_no_location",
      "origin_id": "DD009999",
      "direction": "rx",
      "packet_hash": "abc123",
      "decoder_meta": {
        "payloadType": 5,
        "routeType": 0,
        "messageHash": "abc123",
        "path": ["AB"],
      },
    }

  monkeypatch.setattr(app, "_try_parse_payload", _parse)

  tx_msg = _DummyMsg("meshcore/BOS/CC001111/tx/packets")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, tx_msg)

  rx_msg = _DummyMsg("meshcore/BOS/EE002222/packets")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, rx_msg)

  route_events = [event for event in queue.events if event.get("type") == "route"]
  assert len(route_events) >= 2
  assert route_events[-1]["origin_id"] == "E8D10001"
  assert route_events[-1]["receiver_id"] == "EE002222"


def test_route_event_includes_sender_name_from_packet(monkeypatch):
  _clear_runtime_state()
  queue = _DummyQueue()
  monkeypatch.setattr(app, "update_queue", queue)
  monkeypatch.setattr(
    app,
    "_try_parse_payload",
    lambda *_args, **_kwargs: (
      None,
      {
        "result": "decoded_no_location",
        "origin_id": "CC001111",
        "direction": "rx",
        "packet_hash": "sendername1",
        "decoder_meta": {
          "payloadType": 5,
          "routeType": 0,
          "messageHash": "sendername1",
          "senderName": "yellowcooln",
          "path": ["AB"],
        },
      },
    ),
  )

  msg = _DummyMsg("meshcore/BOS/DD001111/packets")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, msg)

  route_events = [event for event in queue.events if event.get("type") == "route"]
  assert route_events
  assert route_events[0]["sender_name"] == "yellowcooln"


def test_route_event_prefers_packet_hash_for_route_identity(monkeypatch):
  _clear_runtime_state()
  queue = _DummyQueue()
  monkeypatch.setattr(app, "update_queue", queue)
  monkeypatch.setattr(
    app,
    "_try_parse_payload",
    lambda *_args, **_kwargs: (
      None,
      {
        "result": "decoded_no_location",
        "origin_id": "CC001111",
        "direction": "rx",
        "packet_hash": "7232623D62E7848D",
        "decoder_meta": {
          "payloadType": 5,
          "routeType": 0,
          "messageHash": "82BD7767",
          "path": ["AB"],
        },
      },
    ),
  )

  msg = _DummyMsg("meshcore/BOS/DD001111/packets")
  app.mqtt_on_message(None, {"loop": _DummyLoop()}, msg)

  route_events = [event for event in queue.events if event.get("type") == "route"]
  assert route_events
  assert route_events[0]["message_hash"] == "7232623D62E7848D"
