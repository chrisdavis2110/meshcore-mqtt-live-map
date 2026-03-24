import json
import math
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from config import (
  MAP_BOUNDARY_FILE,
  MAP_BOUNDARY_MODE,
  MAP_RADIUS_KM,
  MAP_START_LAT,
  MAP_START_LON,
)

BoundaryPoint = Tuple[float, float]

_boundary_cache: Dict[str, Any] = {
  "loaded": False,
  "path": None,
  "mtime": None,
  "name": "",
  "points": [],
}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
  r = 6371000.0
  p1 = math.radians(lat1)
  p2 = math.radians(lat2)
  dp = math.radians(lat2 - lat1)
  dl = math.radians(lon2 - lon1)
  a = math.sin(dp / 2.0)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0)**2
  return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _normalize_boundary_points(raw_points: Any) -> List[BoundaryPoint]:
  points: List[BoundaryPoint] = []
  if not isinstance(raw_points, list):
    return points
  for item in raw_points:
    lat_val = None
    lon_val = None
    if isinstance(item, (list, tuple)) and len(item) >= 2:
      lat_val = item[0]
      lon_val = item[1]
    elif isinstance(item, dict):
      lat_val = item.get("lat")
      lon_val = item.get("lon")
    try:
      lat = float(lat_val)
      lon = float(lon_val)
    except (TypeError, ValueError):
      continue
    points.append((lat, lon))
  if len(points) >= 2 and points[0] == points[-1]:
    points = points[:-1]
  return points


def load_map_boundary(force: bool = False) -> None:
  cache = _boundary_cache
  cache_path = MAP_BOUNDARY_FILE
  if MAP_BOUNDARY_MODE != "polygon":
    cache.update({
      "loaded": True,
      "path": cache_path,
      "mtime": None,
      "name": "",
      "points": [],
    })
    return

  try:
    stat = os.stat(cache_path)
  except OSError:
    cache.update({
      "loaded": True,
      "path": cache_path,
      "mtime": None,
      "name": "",
      "points": [],
    })
    return

  mtime = stat.st_mtime
  if (
    not force and cache.get("loaded") and cache.get("path") == cache_path and
    cache.get("mtime") == mtime
  ):
    return

  try:
    with open(cache_path, "r", encoding="utf-8") as handle:
      payload = json.load(handle)
  except Exception:
    cache.update({
      "loaded": True,
      "path": cache_path,
      "mtime": mtime,
      "name": "",
      "points": [],
    })
    return

  if isinstance(payload, dict):
    name = str(payload.get("name") or "").strip()
    raw_points = payload.get("points")
  else:
    name = ""
    raw_points = payload

  cache.update({
    "loaded": True,
    "path": cache_path,
    "mtime": mtime,
    "name": name,
    "points": _normalize_boundary_points(raw_points),
  })


def get_map_boundary_name() -> str:
  load_map_boundary()
  return str(_boundary_cache.get("name") or "")


def get_map_boundary_points() -> List[BoundaryPoint]:
  load_map_boundary()
  points = _boundary_cache.get("points") or []
  return [(float(lat), float(lon)) for lat, lon in points]


def _within_polygon(lat: float, lon: float, points: Sequence[BoundaryPoint]) -> bool:
  if len(points) < 3:
    return True
  inside = False
  x = lon
  y = lat
  j = len(points) - 1
  for i, (lat_i, lon_i) in enumerate(points):
    lat_j, lon_j = points[j]
    yi = lat_i
    yj = lat_j
    xi = lon_i
    xj = lon_j
    intersects = ((yi > y) != (yj > y)) and (
      x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
    )
    if intersects:
      inside = not inside
    j = i
  return inside


def within_map_boundary(lat: Any, lon: Any) -> bool:
  try:
    lat_val = float(lat)
    lon_val = float(lon)
  except (TypeError, ValueError):
    return False

  if MAP_BOUNDARY_MODE == "polygon":
    return _within_polygon(lat_val, lon_val, get_map_boundary_points())

  if MAP_RADIUS_KM <= 0:
    return True
  distance_m = _haversine_m(MAP_START_LAT, MAP_START_LON, lat_val, lon_val)
  return distance_m <= (MAP_RADIUS_KM * 1000.0)
