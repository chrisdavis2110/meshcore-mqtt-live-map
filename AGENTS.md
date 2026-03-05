# Repository Guidelines

## Project Structure & Module Organization
- `backend/` contains the app runtime:
  - `app.py` (FastAPI app, MQTT lifecycle, websocket broadcast)
  - `decoder.py` (MeshCore decode + route/path handling)
  - `history.py`, `los.py`, `config.py`, `state.py` (support modules)
  - `static/` (frontend assets: `index.html`, `app.js`, `styles.css`, `sw.js`)
- `data/` stores runtime state files (for example `state.json`, `route_history.jsonl`).
- Root docs: `README.md`, `docs.md`, `howto.md`, `ARCHITECTURE.md`, `VERSIONS.md`, `VERSION.txt`.
- Runtime/deploy files: `docker-compose.yaml`, `.env.example`.

## Build, Test, and Development Commands
- `docker compose up -d --build` builds and starts the app (default workflow).
- `docker compose logs -f meshmap-live` tails backend logs.
- `curl -s http://localhost:8080/snapshot` checks live node/route state.
- `curl -s http://localhost:8080/stats` checks ingest counters.
- `python3 -m py_compile backend/*.py` validates Python syntax.
- `node --check backend/static/app.js` validates frontend JS syntax.
- `pip install -r requirements-dev.txt && pytest -q` runs backend unit tests.

## Coding Style & Naming Conventions
- Use 2-space indentation across Python/JS/CSS/HTML.
- Python: keep lines readable, prefer small helper functions, use `snake_case`.
- JavaScript: keep UI logic explicit and defensive; avoid hidden side effects.
- Keep config names uppercase and environment-driven (`ROUTE_*`, `MQTT_*`, etc.).
- Update docs when changing behavior or env vars.

## Testing Guidelines
- Use `pytest` for backend unit tests and keep manual UI verification in place.
- Minimum checks after changes:
  - Build starts cleanly.
  - `/snapshot` and `/stats` return expected data.
  - UI behavior is validated for touched features (routes, hops, toggles, tools).
- For routing changes, verify hop rendering and direction with live/dev traffic.

## Commit & Pull Request Guidelines
- Follow existing history style: short, imperative messages (examples: `Add ...`, `Fix ...`, `Docs: ...`, `Changelog: ...`).
- Keep commits focused (code + related docs together).
- PRs should include:
  - What changed and why.
  - Any env/config impacts.
  - Validation steps run.
  - Screenshots/GIFs for UI changes.
