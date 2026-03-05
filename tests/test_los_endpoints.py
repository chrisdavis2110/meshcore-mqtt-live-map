import app


def test_los_rejects_invalid_coordinates():
  response = app.line_of_sight(
    lat1=float("nan"),
    lon1=-71.0,
    lat2=42.0,
    lon2=-71.1,
  )
  assert response["ok"] is False
  assert response["error"] == "invalid_coords"


def test_los_returns_profile_when_elevations_are_available(monkeypatch):
  def fake_fetch(points):
    return [0.0 for _ in points], None

  monkeypatch.setattr(app, "_fetch_elevations", fake_fetch)

  response = app.line_of_sight(
    lat1=42.3601,
    lon1=-71.0589,
    lat2=42.3611,
    lon2=-71.0579,
    profile=True,
    h1=5.0,
    h2=5.0,
  )

  assert response["ok"] is True
  assert response["distance_m"] > 0
  assert "profile" in response
  assert "profile_points" in response
  assert isinstance(response["blocked"], bool)


def test_los_elevations_validates_and_returns_results(monkeypatch):
  def fake_fetch(points):
    return [12.3 for _ in points], None

  monkeypatch.setattr(app, "_fetch_elevations", fake_fetch)

  error = app.los_elevations(locations="")
  assert error["status"] == "ERROR"
  assert error["error"] == "missing_locations"

  success = app.los_elevations(locations="42.3601,-71.0589|42.3611,-71.0579")
  assert success["status"] == "OK"
  assert len(success["results"]) == 2
  assert success["results"][0]["elevation"] == 12.3
