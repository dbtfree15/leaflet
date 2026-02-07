# Flyer Distribution Route Planner — Technical Spec

## 1. Overview

A lightweight web application that divides a geographic area into balanced delivery zones, generates driving or walking routes through each zone, and estimates flyer counts per route based on housing/building density. Designed for one-time or occasional use — functional over polished.

---

## 2. Core Workflow

```
Define Area → Set Parameters → Generate Zones → Generate Routes → Export
```

1. User defines a target area (draw polygon OR center point + radius)
2. User inputs: number of routes, total flyers, driving vs walking
3. System divides area into N balanced zones (weighted by estimated address density)
4. System generates an optimized path through each zone's road network
5. User views, prints, or exports routes

---

## 3. Inputs

### 3.1 Area Definition (two modes)

| Mode | UI | Data Captured |
|---|---|---|
| **Center + Radius** | Click map or type address/coords → slider or input for radius (miles/km) | `{ lat, lng, radius_m }` |
| **Draw Polygon** | Click points on map to draw a closed polygon | `[ {lat, lng}, ... ]` array of vertices |

Both modes produce a **bounding geometry** used for all downstream steps.

### 3.2 Job Parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `num_routes` | integer | 4 | Number of zones/routes to generate (1–20) |
| `total_flyers` | integer | 1000 | Total flyers to distribute across all routes |
| `travel_mode` | enum | `walking` | `driving` or `walking` — applies to all routes in the job |

### 3.3 Optional Parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `start_point` | lat/lng | Area centroid | Where each route should start (e.g., parking lot, office) |
| `return_to_start` | boolean | false | Whether routes should loop back to the start point |
| `road_types` | multi-select | all residential | Filter: residential, secondary, tertiary (avoids highways) |
| `balance_priority` | enum | `density` | `density` (equal flyers per route) or `area` (equal geographic size) |

---

## 4. Processing Pipeline

### 4.1 Road Network Extraction

- **Source**: OpenStreetMap via Overpass API (or pre-downloaded `.osm.pbf` via `osmnx`)
- **Process**:
  1. Query all drivable/walkable roads within the bounding geometry
  2. Build a `networkx` graph (nodes = intersections, edges = road segments)
  3. Filter by road type (exclude motorways, trunk roads)
  4. Tag each edge with length (meters) and estimated address count

### 4.2 Housing/Building Density Estimation

**Primary method — OSM building data**:
- Query OSM for all buildings tagged `building=residential`, `building=apartments`, `building=house`, etc. within the area
- Count buildings per grid cell or per road segment (assign buildings to nearest road edge)
- For apartment buildings, estimate units using `building:levels` tag if available (heuristic: ~4 units per floor for apartments, 1 unit for houses)

**Fallback method — Road length proxy**:
- If building data is sparse, estimate density from road classification:
  - `residential` roads: ~20 addresses per 100m (suburban), ~40/100m (urban)
  - `living_street`: ~30 addresses per 100m
  - `service`, `track`: ~2 addresses per 100m
- User can toggle a density multiplier (suburban/urban/rural) to calibrate

**Output**: Each road segment gets an `estimated_addresses` attribute.

### 4.3 Zone Division (Balanced Partitioning)

**Goal**: Split the road network graph into `num_routes` subgraphs where each zone has approximately equal `estimated_addresses` (or equal area, per user setting).

**Algorithm**:

1. **Grid seed**: Overlay a grid on the area, compute address density per cell
2. **K-means clustering** (weighted): Cluster road segment midpoints into `num_routes` clusters, weighted by `estimated_addresses`, using a balanced k-means variant
3. **Graph-connected cleanup**: Ensure each zone is a connected subgraph — reassign orphan segments to the nearest connected zone
4. **Balance pass**: Iteratively swap boundary segments between adjacent zones to equalize the weight metric (addresses or area) within a ±15% tolerance

**Alternative (simpler)**: Use a recursive bisection approach:
1. Sort all road segments by geographic position (alternating lat/lng splits)
2. Recursively split into halves by cumulative address weight until `num_routes` zones exist
3. Fix connectivity

Each zone is stored as a subgraph with metadata:
```json
{
  "zone_id": 1,
  "estimated_addresses": 245,
  "assigned_flyers": 250,
  "total_road_length_m": 4800,
  "geometry": "MultiLineString(...)"  
}
```

### 4.4 Route Generation (per zone)

**Goal**: Generate a path that traverses all (or most) roads in the zone — essentially a variant of the Chinese Postman Problem / Route Inspection Problem.

**Algorithm**:

1. **Start node**: Nearest node to `start_point` (or zone centroid)
2. **Solve approximate Chinese Postman**:
   - Find all odd-degree nodes in the zone subgraph
   - Compute minimum-weight perfect matching on odd-degree nodes
   - Add matched edges (duplicated traversals) to make the graph Eulerian
   - Find Eulerian circuit starting from start node
3. **Simplify**: Remove excessive backtracking where possible; for walking routes, allow one-way traversal of streets (you can deliver to both sides)
4. **If `return_to_start`**: Ensure circuit returns to start node
5. **If not `return_to_start`**: Find Eulerian path (open) instead, or trim the return leg

**Walking mode adjustments**:
- Treat all edges as undirected (pedestrians ignore one-way)
- Include footpaths, pedestrian ways
- Prefer one traversal per street (both sides reachable on foot)

**Driving mode adjustments**:
- Respect one-way streets
- Prefer right-turn-heavy routes where possible (less time)
- May need to traverse some streets twice (each side)

**Output per route**:
```json
{
  "route_id": 1,
  "zone_id": 1,
  "travel_mode": "walking",
  "estimated_addresses": 245,
  "assigned_flyers": 250,
  "total_distance_m": 5200,
  "estimated_duration_min": 65,
  "geometry": "LineString(...)",
  "turn_by_turn": [
    { "instruction": "Head north on Maple St", "distance_m": 120 },
    { "instruction": "Turn right onto Oak Ave", "distance_m": 340 },
    ...
  ],
  "waypoints": [ { "lat": 40.123, "lng": -74.456 }, ... ]
}
```

### 4.5 Flyer Allocation

```
flyers_per_route[i] = round(total_flyers * (zone[i].estimated_addresses / total_estimated_addresses))
```

Adjust rounding so the sum equals `total_flyers` exactly.

---

## 5. Outputs

### 5.1 Interactive Map View

- **Library**: Leaflet.js with OpenStreetMap tiles
- Each zone shown as a shaded polygon in a distinct color
- Route path drawn as a colored polyline on top
- Click a zone to see: route #, flyer count, distance, estimated time
- Legend with all routes

### 5.2 Printable Turn-by-Turn Directions

- One page per route (HTML → print CSS or generated PDF)
- Header: Route #, zone color, flyer count, total distance, estimated time
- Numbered step-by-step directions
- Optional small overview map per route

### 5.3 Exportable Formats

| Format | Use Case | Method |
|---|---|---|
| **GPX** | Import into GPS apps, Garmin, etc. | Generate `.gpx` XML with waypoints + track |
| **Google Maps link** | Open in Google Maps on phone | Build a directions URL with waypoints: `https://www.google.com/maps/dir/lat1,lng1/lat2,lng2/...` (max ~25 waypoints per URL; chain if needed) |
| **KML** | Google Earth, other GIS tools | Generate `.kml` with styled paths |
| **GeoJSON** | Developer-friendly, re-importable | Export full route + zone data |

**Google Maps link construction**:
- Subsample route into ≤23 intermediate waypoints (evenly spaced along route)
- Format: `https://www.google.com/maps/dir/?api=1&origin=LAT,LNG&destination=LAT,LNG&waypoints=LAT,LNG|LAT,LNG|...&travelmode=walking`
- If route exceeds waypoint limit, split into segments with separate links

---

## 6. Tech Stack

### Recommended: Python backend + simple web frontend

```
┌─────────────────────────────────────────┐
│            Browser (Frontend)            │
│  Leaflet.js map + vanilla HTML/JS       │
│  or simple React/Svelte page            │
├─────────────────────────────────────────┤
│          Python Backend (FastAPI)        │
│  /api/generate-routes  POST             │
│  /api/export/{format}  GET              │
├─────────────────────────────────────────┤
│            Core Libraries               │
│  osmnx — OSM road network download      │
│  networkx — graph algorithms            │
│  shapely — geometry operations           │
│  scikit-learn — k-means clustering      │
│  geopy — geocoding                       │
│  gpxpy — GPX export                      │
│  simplekml — KML export                  │
│  folium — map rendering (alt to Leaflet)│
└─────────────────────────────────────────┘
```

### Alternative: Pure Python script (no web UI)

- Use `folium` to generate an interactive HTML map as output
- CLI inputs via `argparse` or a simple config YAML
- Exports saved as files to disk
- Simpler to build, slightly less convenient to use

### Recommendation

Go with the **FastAPI + Leaflet** web app. It's not much more work than the script approach and makes the draw-on-map input possible. Can run locally via `python main.py` — no deployment needed.

---

## 7. Key Dependencies & Data Sources

| Need | Source | Cost |
|---|---|---|
| Road network | OpenStreetMap via `osmnx` | Free |
| Building footprints | OpenStreetMap via Overpass API | Free |
| Geocoding (address → coords) | Nominatim (OSM) | Free, rate-limited |
| Map tiles (display) | OSM tile server or Stamen/CartoDB | Free |
| Route optimization | `networkx` algorithms | Free |
| Directions (fallback) | OSRM (open source) or Google Directions API | Free / $5 per 1k requests |

**Optional paid upgrade**: Google Maps Directions API for more polished turn-by-turn directions (the open-source route will be geometrically correct but directions text may be rougher).

---

## 8. Data Flow Diagram

```
User Input                    Processing                         Output
──────────                    ──────────                         ──────
                                                                  
Center+Radius ──┐                                                 
                ├─► Bounding    ──► Fetch OSM     ──► Build       
Draw Polygon ───┘    Geometry       Roads +           Graph       
                                    Buildings                     
                                                       │          
num_routes ─────────────────────────────────────► Zone            
total_flyers ───────────────────────────────────► Partition       
                                                       │          
                                                  Route per  ──► Map View
travel_mode ──────────────────────────────────►   Zone       ──► Directions
start_point ──────────────────────────────────►   (Chinese   ──► GPX
return_to_start ──────────────────────────────►    Postman)  ──► Google Links
                                                             ──► KML/GeoJSON
```

---

## 9. Estimation Accuracy Notes

- **OSM building data quality varies by region**. Urban US/EU areas typically have excellent coverage. Rural areas may be sparse → falls back to road-length heuristic.
- **Address count is always an estimate**. Expect ±20-30% accuracy. For better accuracy, could optionally integrate county parcel/assessor data (usually free but format varies by jurisdiction).
- **Route efficiency won't be perfect**. The Chinese Postman solution minimizes total distance but the actual walking/driving order may feel suboptimal in spots. Good enough for flyer distribution.

---

## 10. MVP Scope vs. Nice-to-Haves

### MVP (build this)

- [x] Center + radius input with map
- [x] Draw polygon input
- [x] OSM road network fetch + graph build
- [x] Building-density-weighted zone partitioning
- [x] Route generation per zone (Chinese Postman variant)
- [x] Flyer count allocation per route
- [x] Colored map display (Leaflet or Folium)
- [x] Google Maps link export
- [x] GPX export
- [x] Printable directions page

### Nice-to-Have (skip unless easy)

- [ ] Drag zone boundaries to manually adjust
- [ ] Per-route travel mode (mix driving and walking in one job)
- [ ] Avoid specific roads/areas (exclusion zones)
- [ ] Multi-start-points (different people start from different locations)
- [ ] Progress tracking (mark streets as completed)
- [ ] OSRM integration for better turn-by-turn text
- [ ] Import existing address lists (CSV) instead of estimating

---

## 11. File Structure (suggested)

```
flyer-route-planner/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── area.py              # Geometry handling (circle, polygon)
│   ├── network.py           # OSM fetch + graph building (osmnx)
│   ├── density.py           # Building/address density estimation
│   ├── partition.py         # Zone division algorithm
│   ├── routing.py           # Chinese Postman route generation
│   ├── directions.py        # Turn-by-turn instruction generation
│   ├── export.py            # GPX, KML, GeoJSON, Google Maps links
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Single page app
│   ├── app.js               # Map interaction, API calls
│   └── style.css            # Minimal styling + print CSS
└── README.md
```

---

## 12. API Endpoints

### `POST /api/generate`

**Request:**
```json
{
  "area": {
    "type": "circle",
    "center": { "lat": 40.7128, "lng": -74.0060 },
    "radius_m": 2000
  },
  "num_routes": 4,
  "total_flyers": 1000,
  "travel_mode": "walking",
  "start_point": { "lat": 40.7128, "lng": -74.0060 },
  "return_to_start": false,
  "balance_priority": "density"
}
```

**Response:**
```json
{
  "job_id": "abc123",
  "zones": [
    {
      "zone_id": 1,
      "color": "#e74c3c",
      "estimated_addresses": 245,
      "assigned_flyers": 250,
      "boundary": { "type": "Polygon", "coordinates": [...] }
    }
  ],
  "routes": [
    {
      "route_id": 1,
      "zone_id": 1,
      "assigned_flyers": 250,
      "total_distance_m": 5200,
      "estimated_duration_min": 65,
      "geometry": { "type": "LineString", "coordinates": [...] },
      "turn_by_turn": [
        { "instruction": "Head north on Maple St", "distance_m": 120 },
        { "instruction": "Turn right onto Oak Ave", "distance_m": 340 }
      ],
      "google_maps_url": "https://www.google.com/maps/dir/...",
      "waypoints": [ [40.123, -74.456], ... ]
    }
  ],
  "summary": {
    "total_addresses_estimated": 980,
    "total_distance_m": 19400,
    "total_estimated_duration_min": 243
  }
}
```

### `GET /api/export/{job_id}/{format}`

- `format`: `gpx`, `kml`, `geojson`, `pdf`
- Optional query param: `?route_id=2` to export a single route
- Returns file download

---

## 13. Quick Start (for the builder)

```bash
# 1. Set up environment
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn osmnx networkx shapely scikit-learn gpxpy simplekml geopy folium

# 2. Run
cd backend && uvicorn main:app --reload --port 8000

# 3. Open browser
open http://localhost:8000
```

Estimated build time for MVP: **2–4 days** for an experienced Python developer, or **1–2 days** with AI coding assistance.
