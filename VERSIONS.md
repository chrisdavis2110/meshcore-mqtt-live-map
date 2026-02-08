# Versions

## v1.3.5 (02-06-2026)
- Added dual stale-window support so `DEVICE_TTL_HOURS` and `PATH_TTL_SECONDS` work together instead of replacing each other.
- Node pruning now supports both windows at once (with 4-day device defaults and 48-hour path defaults in examples/compose).
- Environment docs and examples now describe the `DEVICE_TTL_HOURS` + `PATH_TTL_SECONDS` model and default values.
- Added `DEVICE_COORDS_FILE` config path support (default: `/data/device_coords.json`) in compose and env docs.
- Credit: `PATH_TTL_SECONDS` flow by https://github.com/djp3.
- Credit: `DEVICE_TTL_HOURS` flow by https://github.com/chrisdavis2110.

## v1.3.1 (02-03-2026)
- Propagation tool now includes an adjustable **TX antenna gain (dBi)** field that feeds directly into range and coverage calculations.
- Propagation defaults now start with **Rx AGL = 1m** (previously 5m).
- Credit: C2D.

## v1.3.0 (02-03-2026)
- LOS tool now supports realtime endpoint dragging with throttled live recompute for smoother interaction (PR #18, credit: https://github.com/mitchellmoss).
- Added elevation fetch proxy endpoint (`/los/elevations`) with frontend caching/backoff to reduce API spam and avoid elevation rate-limit failures while dragging.
- Added `LOS_ELEVATION_PROXY_URL` env/config support so LOS elevation requests can be routed through the backend.
- Fixed LOS point repositioning so you can click/select point A/B and click the map to move that specific point (plus visual selected-point highlight).
- Updated LOS docs and feature notes for the new realtime drag + proxy workflow.

## v1.2.6 (02-02-2026)
- API compatibility update for MeshBuddy and similar clients:
  - `/api/nodes` now defaults to a flat payload (`"data": [...]`).
  - Added top-level `"nodes": [...]` alias for legacy consumers.
  - `updated_since` now applies delta filtering automatically.
  - `mode=full` (or `all`/`snapshot`) forces full list responses.
  - `format=nested` returns wrapped payloads (`"data":{"nodes":[...]}`).

## v1.2.5 (02-02-2026)
- Route line IDs are now observer-aware (`message_hash:receiver_id`) so simultaneous receptions from multiple MQTT observers do not overwrite each other.
- WebSocket auth now accepts `?auth=<turnstile_token>` in addition to cookie/header auth, reducing reconnect loops during Turnstile-gated sessions.
- PROD token checks now always require `PROD_TOKEN` for protected API routes; Turnstile session auth no longer bypasses API token requirements.
- `ROUTE_INFRA_ONLY` endpoint logic was relaxed so direct routes can still render when at least one endpoint is infrastructure (repeater/room).

## v1.2.4 (01-29-2026)
- Turnstile auth now grants access to `/snapshot`, `/stats`, `/peers`, and WebSocket without requiring a PROD token (prevents WS reconnect spam).
- Show Hops panel now includes total route distance (sum of hop-to-hop segments) and updates live with unit toggles.

## v1.2.2 (01-29-2026)
- Fix: Route lines now rely only on decoded packet paths, avoiding MQTT observer/receiver fallback links.
- Fix: Turnstile can enable when `PROD_MODE=true` by passing `PROD_MODE`/`PROD_TOKEN` into the container.
- UI: Added `darkreader-lock` meta on the map + landing pages to prevent Dark Reader overrides.

## v1.2.1 (01-29-2026)
- Feature: Display hop numbers on route paths with a toggle button (credit: https://github.com/slack-t).
- Feature: Consistent hop coloring based on route hash (credit: https://github.com/slack-t).
- Feature: Route details panel with hop list, hash byte IDs, and per-hop/cumulative distance (credit: https://github.com/slack-t).
- Fix: Route details updates live when hops arrive and respects km/mi unit toggles.
- Fix: Route details panel now stacks with other tools (no overlap); LOS panel is scrollable.

## v1.2.0 (01-27-2026)
- Add Cloudflare Turnstile protection with a landing/verification flow and auth cookie.
- Turnstile now only activates when `PROD_MODE=true` (even if `TURNSTILE_ENABLED=true`).
- Preserve Discord/social embeds by allowlisting common bots via user-agent bypass.
- Hide the Turnstile site key from the page while still providing it to the widget.
- Credit: Nasticator (PR #13).
- New envs:
  - `TURNSTILE_ENABLED`
  - `TURNSTILE_SITE_KEY`
  - `TURNSTILE_SECRET_KEY`
  - `TURNSTILE_API_URL`
  - `TURNSTILE_TOKEN_TTL_SECONDS`
  - `TURNSTILE_BOT_BYPASS`
  - `TURNSTILE_BOT_ALLOWLIST`

## v1.1.2 (01-27-2026)
- Dev route debug: route lines are now clickable (when `PROD_MODE=false`) and log rich hop-by-hop details to the browser console (distance, hops, hashes, origin/receiver, timestamps). Credit: https://github.com/sefator (PR #14).

## v1.1.1 (01-26-2026)
- Fix: First-hop route selection now prefers the closest repeater/room to the origin when short-hash collisions occur, preventing cross-city mis-picks (Issue: https://github.com/yellowcooln/meshcore-mqtt-live-map/issues/11).

## v1.1.0 (01-21-2026)
- History panel can be dismissed with an X while keeping history lines visible (re-open via History tool).
- Bump service worker cache and asset version to ensure the new History panel behavior loads.

## v1.0.9 (01-16-2026)
- Enforce `ROUTE_MAX_HOP_DISTANCE` for fallback-selected hops to prevent unrealistic jumps (credit: https://github.com/sefator).

## v1.0.8 (01-14-2026)
- Enforce `ROUTE_MAX_HOP_DISTANCE` across fallback hops, direct routes, and receiver appends to prevent cross-region path jumps.

## v1.0.7 (01-14-2026)
- Route hash collisions now prefer known neighbor pairs before falling back to closest-hop selection.
- Add optional neighbor override map via `NEIGHBOR_OVERRIDES_FILE` (default `data/neighbor_overrides.json`).
- Neighbor edges auto-expire using `DEVICE_TTL_SECONDS` (legacy env name, now `DEVICE_TTL_HOURS`) to prevent stale adjacency picks.

## v1.0.6 (01-13-2026)
- Peers panel now labels line colors (blue = incoming, purple = outgoing).
- Propagation origins can be removed individually by clicking their markers.
- HUD scrollbars styled in Chromium for a cleaner look.
- Bump PWA cache version to force asset refresh.
- Suggestions from Zaos.

## v1.0.5 (01-13-2026)
- Resolve short-hash collisions by choosing the closest node in the route chain (credit: https://github.com/sefator)
- Drop hops that exceed `ROUTE_MAX_HOP_DISTANCE` to avoid unrealistic jumps
- Add `ROUTE_INFRA_ONLY` to restrict route lines to repeaters/rooms
- Document new route env defaults in `.env.example`

## v1.0.4 (01-13-2026)
- Open Graph preview URL no longer double-slashes the `/preview.png` path (credit: https://github.com/chrisdavis2110)
- Preview image now renders in-bounds device dots (not just the center pin; credit: https://github.com/chrisdavis2110)
- Fix preview renderer NameError by importing `Tuple`

## v1.0.3 (01-12-2026)
- Fix route decoding to return the correct tuple when paths exceed max length (credit: https://github.com/sefator)

## v1.0.2 (01-11-2026)
- Fix update banner Hide action by honoring the hidden state in CSS
- Remove update banner debug logging after verification

## v1.0.1 (01-11-2025)
- Update check banner (git local vs upstream) with dismiss + auto recheck every 12 hours
- Custom HUD link button (configurable via env, hidden when unset)
- Update banner rendered from HTML dataset to avoid JS/token fetch issues
- Git repo mounted into container for update checks; safe.directory configured automatically
- Update banner Hide button styled to match HUD controls
- New envs: `CUSTOM_LINK_URL`, `MQTT_ONLINE_FORCE_NAMES`, `GIT_CHECK_ENABLED`, `GIT_CHECK_FETCH`, `GIT_CHECK_PATH`, `GIT_CHECK_INTERVAL_SECONDS`

## v1.0.0 (01-10-2025)
- Live MeshCore node map with MQTT ingest, websocket updates, and Leaflet UI
- Node markers with roles, names, and MQTT online ring
- Trace/path, message, and advert route lines with animations
- Heatmap for recent activity (toggle + intensity slider)
- 24h history tool with heat filter + link weight slider
- Peers tool showing inbound/outbound neighbors with map lines
- LOS tool with elevation profile, peaks, relay suggestion, and mobile support
- Propagation tool with right-side panel and map overlay
- Search, labels toggle, hide nodes, map layer toggles, and shareable URL params
- Distance unit toggle (km/mi) with per-user preference
- PWA install support (manifest + service worker)
- Persistent state + route history on disk
