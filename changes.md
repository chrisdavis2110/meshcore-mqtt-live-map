# Changes

## v1.5.0 (2026-03-07)
- Expanded test coverage from 24 to 44 passing tests.
- Added MQTT online behavior tests:
  - `status` topics mark nodes online even without map coordinates.
  - non-online topics (like `packets`) do not mark MQTT online.
  - existing mapped devices emit `device_seen` websocket updates.
  - forced-online name behavior in `_device_payload` is covered.
- Added websocket auth matrix tests for `PROD_MODE`:
  - query token, access token, bearer header, and `x-token` paths.
  - unauthorized websocket connection closes with code `1008`.
- Added mixed prefix routing tests:
  - unknown hops are skipped while known hops continue.
  - exact 2-byte (`ABCD`) hops are preferred correctly.
- Added neighbor graph tests:
  - manual override edges survive prune while stale observed edges are removed.
  - manual edges retain manual priority after observed updates.
  - neighbor selection priority is validated (`manual > auto > observed`).
- Added persistence robustness tests:
  - corrupt `state.json` does not crash `_load_state`.
  - malformed/stale history lines are skipped and compact flag is set.
- Added weather config injection tests to verify HTML receives env flags for radar/wind combinations.
- Hardened `/coverage` endpoint handling so non-list `keys` payloads now safely return `[]`.
- Weather layer preference persistence: browser now remembers `Radar` and `Wind` on/off states per user via local storage across sessions.
- Replaced deprecated FastAPI startup/shutdown event decorators with a lifespan handler to remove deprecation warnings and keep background task lifecycle clean.
