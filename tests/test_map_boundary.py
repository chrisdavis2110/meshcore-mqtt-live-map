import boundary


def test_within_map_boundary_radius_mode(monkeypatch):
  monkeypatch.setattr(boundary, "MAP_BOUNDARY_MODE", "radius")
  monkeypatch.setattr(boundary, "MAP_RADIUS_KM", 5.0)
  monkeypatch.setattr(boundary, "MAP_START_LAT", 42.3601)
  monkeypatch.setattr(boundary, "MAP_START_LON", -71.0589)

  assert boundary.within_map_boundary(42.3601, -71.0589) is True
  assert boundary.within_map_boundary(42.50, -71.0589) is False


def test_within_map_boundary_polygon_mode(monkeypatch):
  monkeypatch.setattr(boundary, "MAP_BOUNDARY_MODE", "polygon")
  monkeypatch.setattr(
    boundary,
    "get_map_boundary_points",
    lambda: [(42.0, -71.2), (42.4, -71.2), (42.4, -70.8), (42.0, -70.8)],
  )

  assert boundary.within_map_boundary(42.2, -71.0) is True
  assert boundary.within_map_boundary(41.9, -71.0) is False


def test_load_map_boundary_reads_json_file(tmp_path, monkeypatch):
  path = tmp_path / "map_boundary.json"
  path.write_text(
    '{\n'
    '  "name": "SWBC",\n'
    '  "points": [[48.558, -125.475], [48.227, -123.556], [48.286, -123.260]]\n'
    '}\n',
    encoding="utf-8",
  )

  monkeypatch.setattr(boundary, "MAP_BOUNDARY_MODE", "polygon")
  monkeypatch.setattr(boundary, "MAP_BOUNDARY_FILE", str(path))
  boundary.load_map_boundary(force=True)

  assert boundary.get_map_boundary_name() == "SWBC"
  assert boundary.get_map_boundary_points() == [
    (48.558, -125.475),
    (48.227, -123.556),
    (48.286, -123.26),
  ]
