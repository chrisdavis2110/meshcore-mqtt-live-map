import json

import app
import state


def test_neighbor_overrides_load_manual_pairs(tmp_path, monkeypatch):
  state.neighbor_edges.clear()
  path = tmp_path / "neighbor_overrides.json"
  path.write_text(
    json.dumps(
      {
        "AA001111": ["BB001111"],
        "CC001111": "DD001111",
      }
    ),
    encoding="utf-8",
  )

  monkeypatch.setattr(app, "NEIGHBOR_OVERRIDES_FILE", str(path))
  app._load_neighbor_overrides()

  assert state.neighbor_edges["AA001111"]["BB001111"]["manual"] is True
  assert state.neighbor_edges["BB001111"]["AA001111"]["manual"] is True
  assert state.neighbor_edges["CC001111"]["DD001111"]["manual"] is True
  assert state.neighbor_edges["DD001111"]["CC001111"]["manual"] is True


def test_neighbor_prune_keeps_manual_edges_and_removes_stale_observed(monkeypatch):
  state.neighbor_edges.clear()
  monkeypatch.setattr(app, "PATH_TTL_SECONDS", 10)

  app._touch_neighbor("AA001111", "BB001111", ts=900.0, manual=True)
  app._touch_neighbor("AA001111", "CC001111", ts=900.0, manual=False)

  app._prune_neighbors(now=1000.0)

  assert "BB001111" in state.neighbor_edges["AA001111"]
  assert "CC001111" not in state.neighbor_edges["AA001111"]


def test_neighbor_manual_edge_keeps_manual_flag_when_observed(monkeypatch):
  state.neighbor_edges.clear()
  monkeypatch.setattr(app, "PATH_TTL_SECONDS", 30)

  app._touch_neighbor("AA001111", "BB001111", ts=1000.0, manual=True)
  app._touch_neighbor("AA001111", "BB001111", ts=1001.0, manual=False)

  entry = state.neighbor_edges["AA001111"]["BB001111"]
  assert entry["manual"] is True
  assert entry["count"] == 1
  assert entry["last_seen"] == 1001.0
