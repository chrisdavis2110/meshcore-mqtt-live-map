import time

import pytest

import decoder
import state


@pytest.fixture(autouse=True)
def clear_runtime_state():
  state.devices.clear()
  state.seen_devices.clear()
  state.node_hash_candidates.clear()
  state.node_hash_collisions.clear()
  state.node_hash_to_device.clear()
  yield
  state.devices.clear()
  state.seen_devices.clear()
  state.node_hash_candidates.clear()
  state.node_hash_collisions.clear()
  state.node_hash_to_device.clear()


def _add_device(device_id, lat, lon, role="repeater"):
  state.devices[device_id] = state.DeviceState(
    device_id=device_id,
    lat=lat,
    lon=lon,
    ts=time.time(),
    role=role,
  )


def test_normalize_node_hash_supports_one_and_two_byte_prefixes():
  assert decoder._normalize_node_hash("ab") == "AB"
  assert decoder._normalize_node_hash("abcd") == "ABCD"
  assert decoder._normalize_node_hash("0x1") == "01"
  assert decoder._normalize_node_hash(0xAB) == "AB"
  assert decoder._normalize_node_hash(0xABCD) == "ABCD"
  assert decoder._normalize_node_hash("ABCDE") is None


def test_node_hashes_from_device_id_indexes_both_widths():
  assert decoder._node_hashes_from_device_id("ABCD1234") == ["AB", "ABCD"]
  assert decoder._node_hashes_from_device_id("AB12") == ["AB", "AB12"]
  assert decoder._node_hashes_from_device_id("ab") == ["AB"]
  assert decoder._node_hashes_from_device_id("not-hex") == []


def test_rebuild_hash_map_tracks_collisions_and_unique_two_byte_keys():
  _add_device("ABCD1111", 42.0, -71.0)
  _add_device("ABEF2222", 42.001, -71.001)
  _add_device("BC011111", 42.002, -71.002)

  decoder._rebuild_node_hash_map()

  assert state.node_hash_candidates["AB"] == ["ABCD1111", "ABEF2222"]
  assert state.node_hash_candidates["ABCD"] == ["ABCD1111"]
  assert state.node_hash_candidates["ABEF"] == ["ABEF2222"]
  assert state.node_hash_candidates["BC"] == ["BC011111"]
  assert "AB" in state.node_hash_collisions
  assert state.node_hash_to_device["ABCD"] == "ABCD1111"
  assert state.node_hash_to_device["ABEF"] == "ABEF2222"


def test_route_points_from_mixed_prefixes_resolve_in_order():
  _add_device("AA001111", 42.0000, -71.0000, role="repeater")  # origin
  _add_device("ABCD1111", 42.0002, -71.0002, role="repeater")
  _add_device("BC221111", 42.0004, -71.0004, role="repeater")
  _add_device("DD001111", 42.0006, -71.0006, role="repeater")  # receiver
  decoder._rebuild_node_hash_map()

  points, used_hashes, point_ids = decoder._route_points_from_hashes(
    path_hashes=["ABCD", "BC"],
    origin_id="AA001111",
    receiver_id="DD001111",
    ts=time.time(),
  )

  assert points is not None
  assert used_hashes == ["ABCD", "BC"]
  assert point_ids[1:3] == ["ABCD1111", "BC221111"]


def test_route_hashes_reverse_when_receiver_prefix_is_first():
  _add_device("AA001111", 42.0000, -71.0000, role="repeater")  # origin
  _add_device("BC221111", 42.0003, -71.0003, role="repeater")
  _add_device("DD001111", 42.0006, -71.0006, role="repeater")  # receiver
  decoder._rebuild_node_hash_map()

  points, used_hashes, point_ids = decoder._route_points_from_hashes(
    path_hashes=["DD", "BC"],  # receiver hash first (reverse expected)
    origin_id="AA001111",
    receiver_id="DD001111",
    ts=time.time(),
  )

  assert points is not None
  assert used_hashes[0] == "BC"
  assert "BC221111" in point_ids
