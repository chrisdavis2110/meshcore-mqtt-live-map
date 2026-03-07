import math
import time
from typing import Any, Callable, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request

from decoder import _normalize_lat_lon

_radar_country_bounds_cache: Dict[str, Dict[str, Any]] = {}
_RADAR_COUNTRY_BOUNDS_CACHE_TTL_SECONDS = 7 * 24 * 3600


def _radar_bounds_extend(bbox: Dict[str, Optional[float]], coords: Any) -> None:
  if not isinstance(coords, list):
    return
  if (
    len(coords) >= 2 and isinstance(coords[0], (int, float)) and
    isinstance(coords[1], (int, float))
  ):
    lon = float(coords[0])
    lat = float(coords[1])
    if not math.isfinite(lat) or not math.isfinite(lon):
      return
    bbox["south"] = lat if bbox["south"] is None else min(bbox["south"], lat)
    bbox["north"] = lat if bbox["north"] is None else max(bbox["north"], lat)
    bbox["west"] = lon if bbox["west"] is None else min(bbox["west"], lon)
    bbox["east"] = lon if bbox["east"] is None else max(bbox["east"], lon)
    return
  for item in coords:
    _radar_bounds_extend(bbox, item)


def _radar_bounds_from_coords(coords: Any) -> Optional[Dict[str, float]]:
  bbox: Dict[str, Optional[float]] = {
    "south": None,
    "west": None,
    "north": None,
    "east": None,
  }
  _radar_bounds_extend(bbox, coords)
  south = bbox.get("south")
  west = bbox.get("west")
  north = bbox.get("north")
  east = bbox.get("east")
  if (
    south is None or west is None or north is None or east is None or
    south >= north or west >= east
  ):
    return None
  return {
    "south": round(float(south), 6),
    "west": round(float(west), 6),
    "north": round(float(north), 6),
    "east": round(float(east), 6),
  }


def _radar_bounds_from_geojson(
  payload: Any, lat_hint: Optional[float] = None, lon_hint: Optional[float] = None
) -> Optional[Dict[str, float]]:
  geometries: List[Dict[str, Any]] = []
  if not isinstance(payload, dict):
    return None
  payload_type = payload.get("type")
  if payload_type == "FeatureCollection":
    features = payload.get("features") or []
    if isinstance(features, list):
      for feature in features:
        if not isinstance(feature, dict):
          continue
        geometry = feature.get("geometry") or {}
        if isinstance(geometry, dict):
          geometries.append(geometry)
  elif payload_type == "Feature":
    geometry = payload.get("geometry") or {}
    if isinstance(geometry, dict):
      geometries.append(geometry)
  else:
    geometries.append(payload)

  if (
    geometries and lat_hint is not None and lon_hint is not None and
    math.isfinite(lat_hint) and math.isfinite(lon_hint)
  ):
    matching_parts: List[Dict[str, float]] = []
    for geometry in geometries:
      coords = geometry.get("coordinates")
      geom_type = geometry.get("type")
      if geom_type == "Polygon" and isinstance(coords, list):
        part_bounds = _radar_bounds_from_coords(coords)
        if part_bounds:
          matching_parts.append(part_bounds)
      elif geom_type == "MultiPolygon" and isinstance(coords, list):
        for polygon_coords in coords:
          part_bounds = _radar_bounds_from_coords(polygon_coords)
          if part_bounds:
            matching_parts.append(part_bounds)

    matches = [
      item for item in matching_parts
      if item["south"] <= lat_hint <= item["north"] and
      item["west"] <= lon_hint <= item["east"]
    ]
    if matches:
      matches.sort(
        key=lambda item: (
          (item["north"] - item["south"]) * (item["east"] - item["west"])
        )
      )
      return matches[0]

  return _radar_bounds_from_coords([
    geometry.get("coordinates") for geometry in geometries
  ])


def create_weather_router(
  require_prod_token: Callable[[Request], None]
) -> APIRouter:
  router = APIRouter()

  @router.get("/weather/radar/country-bounds")
  async def radar_country_bounds(request: Request, lat: float, lon: float):
    require_prod_token(request)
    normalized = _normalize_lat_lon(lat, lon)
    if not normalized:
      raise HTTPException(status_code=400, detail="invalid_coords")
    lat_val, lon_val = normalized

    try:
      async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=8.0),
        follow_redirects=True,
        headers={"User-Agent": "mesh-live-map/weather"},
      ) as client:
        reverse_resp = await client.get(
          "https://api.bigdatacloud.net/data/reverse-geocode-client",
          params={
            "latitude": f"{lat_val:.6f}",
            "longitude": f"{lon_val:.6f}",
            "localityLanguage": "en",
          },
        )
        reverse_resp.raise_for_status()
        reverse_data = reverse_resp.json()

        iso2 = str(reverse_data.get("countryCode") or "").strip().upper()
        country_name = str(reverse_data.get("countryName") or "").strip()
        if not iso2:
          raise HTTPException(status_code=404, detail="country_not_found")

        now = time.time()
        cache_key = f"{lat_val:.2f},{lon_val:.2f}"
        cached = _radar_country_bounds_cache.get(cache_key)
        if cached and now - float(cached.get("ts", 0.0)
                                 ) <= _RADAR_COUNTRY_BOUNDS_CACHE_TTL_SECONDS:
          return cached.get("payload")

        iso_resp = await client.get(
          f"https://restcountries.com/v3.1/alpha/{iso2}",
          params={"fields": "cca3"},
        )
        iso_resp.raise_for_status()
        iso_data = iso_resp.json()
        if isinstance(iso_data, list):
          iso_data = iso_data[0] if iso_data else {}
        iso3 = str((iso_data or {}).get("cca3") or "").strip().upper()
        if not iso3:
          raise HTTPException(status_code=502, detail="country_iso_lookup_failed")

        boundary_resp = await client.get(
          f"https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM0/"
        )
        boundary_resp.raise_for_status()
        boundary_data = boundary_resp.json()
        geojson_url = str(
          boundary_data.get("simplifiedGeometryGeoJSON") or
          boundary_data.get("gjDownloadURL") or ""
        ).strip()
        if not geojson_url:
          raise HTTPException(status_code=502, detail="country_boundary_missing")

        geojson_resp = await client.get(geojson_url)
        geojson_resp.raise_for_status()
        bounds = _radar_bounds_from_geojson(
          geojson_resp.json(), lat_hint=lat_val, lon_hint=lon_val
        )
        if not bounds:
          raise HTTPException(status_code=502, detail="country_bounds_parse_failed")

        payload = {
          "country_code": iso2,
          "country_iso3": iso3,
          "country_name": country_name,
          "bounds": bounds,
          "boundingbox": [
            bounds["south"],
            bounds["north"],
            bounds["west"],
            bounds["east"],
          ],
          "source": "bigdatacloud+geoboundaries",
        }
        _radar_country_bounds_cache[cache_key] = {"ts": now, "payload": payload}
        return payload
    except HTTPException:
      raise
    except httpx.TimeoutException:
      raise HTTPException(status_code=504, detail="radar_country_lookup_timeout")
    except httpx.HTTPStatusError as exc:
      status_code = exc.response.status_code if exc.response else 502
      raise HTTPException(
        status_code=502,
        detail=f"radar_country_lookup_http_{status_code}",
      )
    except httpx.HTTPError as exc:
      raise HTTPException(
        status_code=502, detail=f"radar_country_lookup_error: {exc}"
      )
    except Exception as exc:
      raise HTTPException(status_code=500, detail=f"radar_country_lookup_failed: {exc}")

  return router
