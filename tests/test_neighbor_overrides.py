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
