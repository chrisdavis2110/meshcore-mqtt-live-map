import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "backend" / "static" / "app.js"
INDEX_HTML = ROOT / "backend" / "static" / "index.html"
STYLES_CSS = ROOT / "backend" / "static" / "styles.css"


def _extract_function(source, name):
  marker = f"function {name}("
  start = source.index(marker)
  brace = source.index("{", start)
  depth = 0
  for index in range(brace, len(source)):
    if source[index] == "{":
      depth += 1
    elif source[index] == "}":
      depth -= 1
      if depth == 0:
        return source[start:index + 1]
  raise AssertionError(f"unterminated function: {name}")


def test_hidden_endpoint_roles_keep_repeater_to_repeater_route_segment():
  source = APP_JS.read_text(encoding="utf-8")
  route_point_role = _extract_function(source, "routePointRole")
  visible_route_segments = _extract_function(source, "visibleRouteSegments")
  script = f"""
const visibleRoles = new Set(['repeater']);
const deviceData = new Map();
const resolveRole = device => device.role || 'unknown';
{route_point_role}
{visible_route_segments}
const meta = {{ points: [
  {{ point_label: 'Companion', role_label: 'companion', endpoint_only: true,
     lat: NaN, lon: NaN }},
  {{ point_label: 'Repeater A', role_label: 'repeater', lat: 2, lon: 2 }},
  {{ point_label: 'Repeater B', role_label: 'repeater', lat: 3, lon: 3 }},
  {{ point_label: 'Room', role_label: 'room', endpoint_only: true,
     lat: 4, lon: 4 }}
] }};
const labels = () => visibleRouteSegments(meta).map(segment =>
    segment.map(point => point.point_label)
  );
const hiddenEndpoints = labels();
visibleRoles.add('companion');
visibleRoles.add('room');
console.log(JSON.stringify({{ hiddenEndpoints, allRoles: labels() }}));
"""

  result = subprocess.run(
    ["node", "-e", script],
    check=True,
    capture_output=True,
    text=True,
  )

  assert json.loads(result.stdout) == {
    "hiddenEndpoints": [["Repeater A", "Repeater B"]],
    "allRoles": [["Repeater A", "Repeater B"]],
  }


def test_room_server_legend_label_uses_title_case():
  html = INDEX_HTML.read_text(encoding="utf-8")

  assert "> Room Server\n" in html
  assert "> Room server\n" not in html


def test_live_route_filter_uses_clear_label():
  html = INDEX_HTML.read_text(encoding="utf-8")

  assert ">Filter Live Routes</label>" in html
  assert ">Route Nodes</label>" not in html


def test_route_node_filter_matches_current_device_name():
  source = APP_JS.read_text(encoding="utf-8")
  route_matches_node_filter = _extract_function(
    source,
    "routeMatchesNodeFilter",
  )
  script = f"""
const routeNodeFilterText = 'Current Repeater Name';
const deviceData = new Map([
  ['AABBCCDD', {{ name: 'Current Repeater Name' }}]
]);
const deviceDisplayName = device => device.name;
{route_matches_node_filter}
const meta = {{
  origin_id: 'AABBCCDD',
  origin_label: 'Old Repeater Name',
  receiver_id: '11223344',
  receiver_label: 'Receiver',
  points: [{{ point_id: 'AABBCCDD', point_label: 'Old Repeater Name' }}],
  hashes: []
}};
console.log(JSON.stringify(routeMatchesNodeFilter(meta)));
"""

  result = subprocess.run(
    ["node", "-e", script],
    check=True,
    capture_output=True,
    text=True,
  )

  assert json.loads(result.stdout) is True


def test_route_node_dropdown_is_positioned_inside_viewport():
  source = APP_JS.read_text(encoding="utf-8")
  position_results = _extract_function(
    source,
    "positionRouteNodeFilterResults",
  )
  script = f"""
const routeNodeFilterInput = {{
  getBoundingClientRect: () => ({{
    left: 22, right: 328, top: 372, bottom: 402, width: 306
  }})
}};
const routeNodeFilterResults = {{
  hidden: false,
  offsetHeight: 202,
  style: {{}}
}};
const window = {{ innerWidth: 1280, innerHeight: 577 }};
{position_results}
positionRouteNodeFilterResults();
console.log(JSON.stringify(routeNodeFilterResults.style));
"""

  result = subprocess.run(
    ["node", "-e", script],
    check=True,
    capture_output=True,
    text=True,
  )
  style = json.loads(result.stdout)

  assert style == {
    "width": "306px",
    "left": "22px",
    "right": "auto",
    "top": "166px",
  }
  css = STYLES_CSS.read_text(encoding="utf-8")
  assert ".route-node-filter-results {\n      position: fixed;" in css


def test_route_node_filter_refresh_does_not_recreate_routes():
  source = APP_JS.read_text(encoding="utf-8")
  sync_filter_displays = _extract_function(
    source,
    "syncRouteFilterDisplays",
  )
  script = f"""
const entries = new Map([['route-a', {{}}], ['route-b', {{}}]]);
const routeLines = entries;
const synced = [];
let statsRefreshes = 0;
const syncRouteEntryDisplay = (id, entry) => synced.push([id, entry]);
const refreshStats = () => {{ statsRefreshes += 1; }};
{sync_filter_displays}
syncRouteFilterDisplays();
console.log(JSON.stringify({{
  size: routeLines.size,
  synced: synced.map(item => item[0]),
  statsRefreshes
}}));
"""

  result = subprocess.run(
    ["node", "-e", script],
    check=True,
    capture_output=True,
    text=True,
  )

  assert json.loads(result.stdout) == {
    "size": 2,
    "synced": ["route-a", "route-b"],
    "statsRefreshes": 1,
  }
