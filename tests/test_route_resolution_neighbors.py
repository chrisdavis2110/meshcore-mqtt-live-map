import time

import decoder
import state


def _add_device(device_id, lat, lon, role="repeater"):
  state.devices[device_id] = state.DeviceState(
    device_id=device_id,
    lat=lat,
    lon=lon,
    ts=time.time(),
    role=role,
  )
  state.seen_devices[device_id] = time.time()


def _clear_state():
  state.devices.clear()
  state.seen_devices.clear()
  state.node_hash_candidates.clear()
  state.node_hash_collisions.clear()
  state.node_hash_to_device.clear()
  state.neighbor_edges.clear()


def test_neighbor_edges_preferred_for_collided_hash_after_first_hop():
  _clear_state()
  try:
    # Origin
    _add_device("AA001111", 42.0000, -71.0000)
    # First hop (unique hash BC)
    _add_device("BC001111", 42.0002, -71.0002)
    # Second hop candidates (collided AB)
    _add_device("ABCD1111", 42.0004, -71.0004)
    _add_device("ABEF2222", 42.0006, -71.0006)
    # Receiver
    _add_device("DD001111", 42.0008, -71.0008)

    decoder._rebuild_node_hash_map()

    # Prefer ABEF2222 for BC001111 -> AB despite collision.
    state.neighbor_edges["BC001111"] = {
      "ABEF2222": {"count": 5, "last_seen": time.time(), "manual": True}
    }

    points, used_hashes, point_ids = decoder._route_points_from_hashes(
      path_hashes=["BC", "AB"],
      origin_id="AA001111",
      receiver_id="DD001111",
      ts=time.time(),
    )

    assert points is not None
    assert used_hashes[:2] == ["BC", "AB"]
    assert len(point_ids) >= 3
    assert point_ids[2] == "ABEF2222"
  finally:
    _clear_state()


def test_choose_neighbor_device_priority_manual_then_auto_then_observed():
  _clear_state()
  try:
    _add_device("AA001111", 42.0000, -71.0000)
    _add_device("BB001111", 42.0001, -71.0001)
    _add_device("CC001111", 42.0002, -71.0002)
    _add_device("DD001111", 42.0003, -71.0003)

    state.neighbor_edges["AA001111"] = {
      "BB001111": {"count": 10, "last_seen": time.time(), "manual": False},
      "CC001111": {"count": 1, "last_seen": time.time(), "manual": False, "auto": True},
      "DD001111": {"count": 0, "last_seen": time.time(), "manual": True},
    }

    picked = decoder._choose_neighbor_device(
      prev_id="AA001111",
      candidates=["BB001111", "CC001111", "DD001111"],
      ref_lat=42.0000,
      ref_lon=-71.0000,
      ts=time.time(),
    )
    assert picked == "DD001111"

    state.neighbor_edges["AA001111"].pop("DD001111")
    picked_auto = decoder._choose_neighbor_device(
      prev_id="AA001111",
      candidates=["BB001111", "CC001111"],
      ref_lat=42.0000,
      ref_lon=-71.0000,
      ts=time.time(),
    )
    assert picked_auto == "CC001111"
  finally:
    _clear_state()
