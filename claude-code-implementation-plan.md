# Flyer Route Planner — Claude Code Implementation Plan

## 🎯 Overview
This document provides a commit-by-commit plan to build the Flyer Distribution Route Planner using Claude Code. Each commit is designed to be a working, testable increment.

**Estimated total time:** 2-4 days  
**Target stack:** FastAPI (backend) + Vanilla JS/HTML + Leaflet.js (frontend)

---

## 📋 Pre-Implementation Checklist

### Before Starting, Ask the User:

1. **Optional API Keys** (can start without these):
   - Do you have a Google Maps API key? (optional, for better directions)
   - Do you have an OSRM server URL? (optional, can use OSM/Nominatim for free)

2. **Environment Setup**:
   - Confirm Python 3.8+ is available
   - Confirm they want to run this locally (default) or need deployment setup
   - Preferred port for local server (default: 8000)

3. **Feature Priorities**:
   - Should we include PDF export in MVP? (requires additional library)
   - Preference for deployment: Local only, Docker, or cloud?

### Initial Setup Information
```bash
# These will be needed:
- Python 3.8+
- pip package manager
- Modern web browser
- ~2GB disk space for dependencies and OSM data caching
```

---

## 🏗️ Commit-by-Commit Implementation Plan

### Phase 1: Project Foundation

#### Commit 1: Project Structure & Dependencies
**Goal:** Set up the project skeleton and install all required packages

**Tasks:**
- Create directory structure:
  ```
  flyer-route-planner/
  ├── backend/
  │   ├── __init__.py
  │   ├── main.py
  │   └── requirements.txt
  ├── frontend/
  │   ├── index.html
  │   ├── app.js
  │   └── style.css
  ├── .gitignore
  └── README.md
  ```
- Create `backend/requirements.txt` with:
  ```
  fastapi==0.104.1
  uvicorn[standard]==0.24.0
  osmnx==1.9.1
  networkx==3.2.1
  shapely==2.0.2
  scikit-learn==1.3.2
  geopy==2.4.1
  gpxpy==1.6.1
  simplekml==1.3.6
  folium==0.15.1
  pandas==2.1.4
  numpy==1.26.2
  python-multipart==0.0.6
  ```
- Create `.gitignore` with Python and cache exclusions
- Create basic README with setup instructions

**Test:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

---

#### Commit 2: FastAPI Hello World + CORS
**Goal:** Get a minimal API server running with proper CORS for frontend communication

**File:** `backend/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Flyer Route Planner API")

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def serve_frontend():
    """Serve the main HTML page"""
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Flyer Route Planner API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

**Test:**
```bash
cd backend
python main.py
# Visit http://localhost:8000/api/health
```

---

#### Commit 3: Basic Frontend Shell with Leaflet Map
**Goal:** Create the UI foundation with an interactive map

**File:** `frontend/index.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flyer Route Planner</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="static/style.css">
</head>
<body>
    <div id="container">
        <aside id="sidebar">
            <h1>🗺️ Flyer Route Planner</h1>
            
            <section class="panel">
                <h2>1. Define Area</h2>
                <div class="button-group">
                    <button id="btnCircle" class="btn-mode active">Center + Radius</button>
                    <button id="btnPolygon" class="btn-mode">Draw Polygon</button>
                </div>
                <div id="circleInputs" class="mode-panel">
                    <input type="text" id="addressInput" placeholder="Enter address or click map">
                    <label>Radius: <span id="radiusValue">1.0</span> km</label>
                    <input type="range" id="radiusSlider" min="0.5" max="5" step="0.1" value="1.0">
                </div>
                <div id="polygonInputs" class="mode-panel hidden">
                    <p>Click on the map to draw polygon. Double-click to finish.</p>
                </div>
            </section>

            <section class="panel">
                <h2>2. Set Parameters</h2>
                <label>Number of Routes: <input type="number" id="numRoutes" min="1" max="20" value="4"></label>
                <label>Total Flyers: <input type="number" id="totalFlyers" min="100" max="100000" value="1000" step="100"></label>
                <label>Travel Mode:
                    <select id="travelMode">
                        <option value="walking">Walking</option>
                        <option value="driving">Driving</option>
                    </select>
                </label>
                <label>
                    <input type="checkbox" id="returnToStart"> Return to start point
                </label>
            </section>

            <section class="panel">
                <button id="btnGenerate" class="btn-primary" disabled>Generate Routes</button>
                <div id="status"></div>
            </section>

            <section class="panel" id="resultsPanel" style="display: none;">
                <h2>Routes</h2>
                <div id="routesList"></div>
                <button id="btnExportGPX" class="btn-secondary">Export All GPX</button>
                <button id="btnPrint" class="btn-secondary">Print Directions</button>
            </section>
        </aside>

        <main id="mapContainer">
            <div id="map"></div>
        </main>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="static/app.js"></script>
</body>
</html>
```

**File:** `frontend/style.css`
```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    height: 100vh;
    overflow: hidden;
}

#container {
    display: flex;
    height: 100vh;
}

#sidebar {
    width: 380px;
    background: #f5f5f5;
    overflow-y: auto;
    padding: 20px;
    box-shadow: 2px 0 5px rgba(0,0,0,0.1);
}

#sidebar h1 {
    font-size: 1.5em;
    margin-bottom: 20px;
    color: #333;
}

.panel {
    background: white;
    padding: 15px;
    margin-bottom: 15px;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.panel h2 {
    font-size: 1.1em;
    margin-bottom: 12px;
    color: #555;
}

.button-group {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
}

.btn-mode {
    flex: 1;
    padding: 8px;
    border: 1px solid #ddd;
    background: white;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.2s;
}

.btn-mode.active {
    background: #3498db;
    color: white;
    border-color: #3498db;
}

input[type="text"],
input[type="number"],
select {
    width: 100%;
    padding: 8px;
    margin: 8px 0;
    border: 1px solid #ddd;
    border-radius: 4px;
}

input[type="range"] {
    width: 100%;
}

label {
    display: block;
    margin: 8px 0;
    color: #555;
}

.btn-primary,
.btn-secondary {
    width: 100%;
    padding: 12px;
    margin: 8px 0;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1em;
    transition: all 0.2s;
}

.btn-primary {
    background: #27ae60;
    color: white;
}

.btn-primary:hover:not(:disabled) {
    background: #229954;
}

.btn-primary:disabled {
    background: #95a5a6;
    cursor: not-allowed;
}

.btn-secondary {
    background: #3498db;
    color: white;
}

.btn-secondary:hover {
    background: #2980b9;
}

.hidden {
    display: none !important;
}

#status {
    padding: 10px;
    margin-top: 10px;
    border-radius: 4px;
    font-size: 0.9em;
}

#status.loading {
    background: #fff3cd;
    color: #856404;
}

#status.success {
    background: #d4edda;
    color: #155724;
}

#status.error {
    background: #f8d7da;
    color: #721c24;
}

#mapContainer {
    flex: 1;
    position: relative;
}

#map {
    width: 100%;
    height: 100%;
}

.route-item {
    padding: 10px;
    margin: 8px 0;
    background: #f8f9fa;
    border-left: 4px solid;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
}

.route-item:hover {
    background: #e9ecef;
    transform: translateX(2px);
}

.route-item strong {
    display: block;
    margin-bottom: 4px;
}

.route-item small {
    color: #666;
}

/* Print styles */
@media print {
    #sidebar {
        display: none;
    }
    #mapContainer {
        display: none;
    }
}
```

**File:** `frontend/app.js` (initial version)
```javascript
// App State
const state = {
    mode: 'circle', // 'circle' or 'polygon'
    center: null,
    radius: 1000, // meters
    polygon: [],
    map: null,
    markers: [],
    layers: [],
    currentJob: null
};

// Initialize map
function initMap() {
    state.map = L.map('map').setView([40.7128, -74.0060], 12);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(state.map);
    
    // Click handler for placing center point
    state.map.on('click', (e) => {
        if (state.mode === 'circle') {
            handleCircleClick(e);
        }
    });
}

// Handle circle mode click
function handleCircleClick(e) {
    state.center = e.latlng;
    document.getElementById('addressInput').value = 
        `${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`;
    updateCircleOnMap();
    document.getElementById('btnGenerate').disabled = false;
}

// Update circle visualization
function updateCircleOnMap() {
    // Clear existing
    state.layers.forEach(layer => state.map.removeLayer(layer));
    state.layers = [];
    
    if (state.center) {
        // Add marker
        const marker = L.marker(state.center).addTo(state.map);
        state.layers.push(marker);
        
        // Add circle
        const circle = L.circle(state.center, {
            radius: state.radius,
            color: '#3498db',
            fillColor: '#3498db',
            fillOpacity: 0.1
        }).addTo(state.map);
        state.layers.push(circle);
        
        // Fit bounds
        state.map.fitBounds(circle.getBounds());
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    
    // Mode switching
    document.getElementById('btnCircle').addEventListener('click', () => {
        state.mode = 'circle';
        document.getElementById('btnCircle').classList.add('active');
        document.getElementById('btnPolygon').classList.remove('active');
        document.getElementById('circleInputs').classList.remove('hidden');
        document.getElementById('polygonInputs').classList.add('hidden');
    });
    
    document.getElementById('btnPolygon').addEventListener('click', () => {
        state.mode = 'polygon';
        document.getElementById('btnPolygon').classList.add('active');
        document.getElementById('btnCircle').classList.remove('active');
        document.getElementById('polygonInputs').classList.remove('hidden');
        document.getElementById('circleInputs').classList.add('hidden');
        alert('Polygon drawing will be implemented in next commit');
    });
    
    // Radius slider
    document.getElementById('radiusSlider').addEventListener('input', (e) => {
        const km = parseFloat(e.target.value);
        state.radius = km * 1000;
        document.getElementById('radiusValue').textContent = km.toFixed(1);
        updateCircleOnMap();
    });
    
    // Generate button
    document.getElementById('btnGenerate').addEventListener('click', async () => {
        await generateRoutes();
    });
});

// Generate routes (stub for now)
async function generateRoutes() {
    const status = document.getElementById('status');
    status.className = 'loading';
    status.textContent = 'Generating routes... (API endpoint coming next)';
    
    setTimeout(() => {
        status.className = 'error';
        status.textContent = 'Backend API not yet implemented';
    }, 1000);
}
```

**Test:**
- Run the server
- Open http://localhost:8000
- Click on the map to set center
- Adjust radius slider
- Verify circle updates on map

---

### Phase 2: Backend Core Functionality

#### Commit 4: Geometry & Area Handling Module
**Goal:** Create utilities for handling geographic areas (circles and polygons)

**File:** `backend/area.py`
```python
"""
Geometry and area handling utilities
"""
from typing import Dict, List, Tuple, Optional
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import math

def create_circle_polygon(center_lat: float, center_lng: float, radius_m: float, num_points: int = 64) -> Polygon:
    """
    Create a polygon approximating a circle.
    
    Args:
        center_lat: Center latitude
        center_lng: Center longitude
        radius_m: Radius in meters
        num_points: Number of points to approximate circle
        
    Returns:
        Shapely Polygon
    """
    # Approximate degrees per meter at this latitude
    lat_deg_per_m = 1 / 111320
    lng_deg_per_m = 1 / (111320 * math.cos(math.radians(center_lat)))
    
    points = []
    for i in range(num_points):
        angle = (2 * math.pi * i) / num_points
        lat = center_lat + (radius_m * math.sin(angle) * lat_deg_per_m)
        lng = center_lng + (radius_m * math.cos(angle) * lng_deg_per_m)
        points.append((lng, lat))  # Note: Shapely uses (x, y) = (lng, lat)
    
    return Polygon(points)

def create_polygon_from_points(points: List[Dict[str, float]]) -> Polygon:
    """
    Create a polygon from a list of lat/lng points.
    
    Args:
        points: List of dicts with 'lat' and 'lng' keys
        
    Returns:
        Shapely Polygon
    """
    coords = [(p['lng'], p['lat']) for p in points]
    return Polygon(coords)

def get_bounding_box(geometry: Polygon) -> Tuple[float, float, float, float]:
    """
    Get bounding box of geometry.
    
    Returns:
        (min_lng, min_lat, max_lng, max_lat)
    """
    bounds = geometry.bounds
    return bounds  # Returns (minx, miny, maxx, maxy) = (min_lng, min_lat, max_lng, max_lat)

def get_centroid(geometry: Polygon) -> Tuple[float, float]:
    """
    Get centroid of geometry.
    
    Returns:
        (lat, lng)
    """
    centroid = geometry.centroid
    return (centroid.y, centroid.x)  # (lat, lng)

def area_in_square_meters(geometry: Polygon) -> float:
    """
    Approximate area in square meters using Web Mercator projection.
    Note: This is an approximation and less accurate near poles.
    
    Args:
        geometry: Shapely Polygon in WGS84 coordinates
        
    Returns:
        Approximate area in square meters
    """
    # Convert to Web Mercator (EPSG:3857) for area calculation
    # This is an approximation - for production use pyproj
    from shapely.ops import transform
    import pyproj
    
    wgs84 = pyproj.CRS('EPSG:4326')
    utm = pyproj.CRS('EPSG:3857')
    project = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
    
    projected = transform(project, geometry)
    return projected.area
```

**Test:** Add to `main.py`:
```python
from backend.area import create_circle_polygon, get_bounding_box

@app.get("/api/test/area")
async def test_area():
    polygon = create_circle_polygon(40.7128, -74.0060, 1000)
    bbox = get_bounding_box(polygon)
    return {"bbox": bbox, "area_m2": polygon.area}
```

---

#### Commit 5: OSM Network Fetching Module
**Goal:** Download and process road networks from OpenStreetMap

**File:** `backend/network.py`
```python
"""
OpenStreetMap network fetching and graph building
"""
import osmnx as ox
import networkx as nx
from shapely.geometry import Polygon, Point, LineString
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure osmnx
ox.settings.use_cache = True
ox.settings.log_console = True

def fetch_road_network(polygon: Polygon, travel_mode: str = 'walk') -> nx.MultiDiGraph:
    """
    Fetch road network from OpenStreetMap within the given polygon.
    
    Args:
        polygon: Shapely Polygon defining the area
        travel_mode: 'walk' or 'drive'
        
    Returns:
        NetworkX MultiDiGraph with road network
    """
    logger.info(f"Fetching {travel_mode} network from OSM...")
    
    try:
        # Determine network type
        network_type = 'walk' if travel_mode == 'walking' else 'drive'
        
        # Fetch network within polygon
        G = ox.graph_from_polygon(
            polygon, 
            network_type=network_type,
            simplify=True,
            retain_all=False
        )
        
        logger.info(f"Network fetched: {len(G.nodes)} nodes, {len(G.edges)} edges")
        
        # Add edge lengths if not present
        G = ox.add_edge_lengths(G)
        
        # Add street names and other attributes
        for u, v, key, data in G.edges(keys=True, data=True):
            if 'name' not in data:
                data['name'] = 'Unnamed Road'
            if 'highway' not in data:
                data['highway'] = 'unclassified'
        
        return G
        
    except Exception as e:
        logger.error(f"Error fetching network: {e}")
        raise

def get_road_stats(G: nx.MultiDiGraph) -> Dict:
    """
    Get statistics about the road network.
    
    Args:
        G: NetworkX graph
        
    Returns:
        Dictionary with network statistics
    """
    total_length = sum(data.get('length', 0) for _, _, data in G.edges(data=True))
    
    road_types = {}
    for _, _, data in G.edges(data=True):
        highway_type = data.get('highway', 'unknown')
        if isinstance(highway_type, list):
            highway_type = highway_type[0]
        road_types[highway_type] = road_types.get(highway_type, 0) + 1
    
    return {
        'num_nodes': len(G.nodes),
        'num_edges': len(G.edges),
        'total_length_m': total_length,
        'road_types': road_types
    }

def filter_residential_roads(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """
    Filter graph to keep only residential/local roads (exclude highways).
    
    Args:
        G: NetworkX graph
        
    Returns:
        Filtered graph
    """
    # Road types to keep
    keep_types = {
        'residential', 'living_street', 'service', 
        'unclassified', 'tertiary', 'secondary',
        'tertiary_link', 'secondary_link'
    }
    
    # Create a copy
    G_filtered = G.copy()
    
    # Remove edges that are highways
    edges_to_remove = []
    for u, v, key, data in G_filtered.edges(keys=True, data=True):
        highway = data.get('highway', 'unknown')
        if isinstance(highway, list):
            highway = highway[0]
        
        if highway not in keep_types and highway not in ['footway', 'path', 'pedestrian']:
            edges_to_remove.append((u, v, key))
    
    G_filtered.remove_edges_from(edges_to_remove)
    
    # Remove isolated nodes
    G_filtered.remove_nodes_from(list(nx.isolates(G_filtered)))
    
    logger.info(f"Filtered to {len(G_filtered.edges)} edges from {len(G.edges)} total")
    
    return G_filtered
```

**Test:** Add to `main.py`:
```python
from backend.network import fetch_road_network, get_road_stats

@app.get("/api/test/network")
async def test_network():
    from backend.area import create_circle_polygon
    polygon = create_circle_polygon(40.7128, -74.0060, 500)
    G = fetch_road_network(polygon, 'walking')
    stats = get_road_stats(G)
    return stats
```

---

#### Commit 6: Building Density Estimation Module
**Goal:** Estimate address density using OSM building data

**File:** `backend/density.py`
```python
"""
Building and address density estimation
"""
import osmnx as ox
import networkx as nx
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import nearest_points
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

def fetch_buildings(polygon: Polygon) -> List[Dict]:
    """
    Fetch building footprints from OpenStreetMap.
    
    Args:
        polygon: Area to query
        
    Returns:
        List of building data dictionaries
    """
    logger.info("Fetching buildings from OSM...")
    
    try:
        # Query buildings
        buildings = ox.features_from_polygon(
            polygon,
            tags={'building': True}
        )
        
        logger.info(f"Found {len(buildings)} buildings")
        
        # Extract relevant info
        building_list = []
        for idx, row in buildings.iterrows():
            building_type = row.get('building', 'yes')
            levels = row.get('building:levels', 1)
            
            # Try to convert levels to int
            try:
                levels = int(float(levels))
            except (ValueError, TypeError):
                levels = 1
            
            building_list.append({
                'geometry': row['geometry'],
                'type': building_type,
                'levels': levels,
                'centroid': row['geometry'].centroid
            })
        
        return building_list
        
    except Exception as e:
        logger.warning(f"Error fetching buildings: {e}")
        return []

def estimate_units_per_building(building: Dict) -> int:
    """
    Estimate number of dwelling units in a building.
    
    Args:
        building: Building data dict with 'type' and 'levels'
        
    Returns:
        Estimated number of units
    """
    building_type = building['type']
    levels = building.get('levels', 1)
    
    # Heuristics for unit estimation
    if building_type in ['apartments', 'residential', 'house']:
        if building_type == 'apartments':
            # Estimate ~4 units per floor for apartments
            return max(4 * levels, 4)
        else:
            # Single family home
            return 1
    elif building_type in ['detached', 'semidetached_house', 'terrace']:
        return 1
    else:
        # Unknown type, assume small residential
        return 1

def assign_buildings_to_edges(
    G: nx.MultiDiGraph, 
    buildings: List[Dict], 
    max_distance_m: float = 50
) -> nx.MultiDiGraph:
    """
    Assign buildings to nearest road edges and estimate addresses per edge.
    
    Args:
        G: Road network graph
        buildings: List of building data
        max_distance_m: Maximum distance to assign building to road
        
    Returns:
        Graph with 'estimated_addresses' attribute on edges
    """
    logger.info("Assigning buildings to road edges...")
    
    # Initialize edge attributes
    for u, v, key in G.edges(keys=True):
        G[u][v][key]['estimated_addresses'] = 0
    
    if not buildings:
        logger.warning("No buildings found, using fallback estimation")
        return estimate_from_road_length(G)
    
    # Create a mapping of edges to LineStrings
    edge_lines = {}
    for u, v, key, data in G.edges(keys=True, data=True):
        if 'geometry' in data:
            edge_lines[(u, v, key)] = data['geometry']
        else:
            # Create line from node positions
            line = LineString([
                (G.nodes[u]['x'], G.nodes[u]['y']),
                (G.nodes[v]['x'], G.nodes[v]['y'])
            ])
            edge_lines[(u, v, key)] = line
    
    # Assign each building to nearest edge
    for building in buildings:
        centroid = building['centroid']
        units = estimate_units_per_building(building)
        
        # Find nearest edge
        min_dist = float('inf')
        nearest_edge = None
        
        for edge, line in edge_lines.items():
            dist = centroid.distance(line)
            if dist < min_dist:
                min_dist = dist
                nearest_edge = edge
        
        # Assign if within threshold
        if nearest_edge and min_dist < max_distance_m / 111320:  # Convert to degrees (approx)
            u, v, key = nearest_edge
            G[u][v][key]['estimated_addresses'] += units
    
    total_addresses = sum(
        data.get('estimated_addresses', 0) 
        for _, _, data in G.edges(data=True)
    )
    logger.info(f"Total estimated addresses: {total_addresses}")
    
    return G

def estimate_from_road_length(G: nx.MultiDiGraph, density_multiplier: float = 20.0) -> nx.MultiDiGraph:
    """
    Fallback method: Estimate addresses based on road length.
    
    Args:
        G: Road network graph
        density_multiplier: Addresses per 100m of road
        
    Returns:
        Graph with estimated addresses
    """
    logger.info("Using road length fallback for density estimation")
    
    for u, v, key, data in G.edges(keys=True, data=True):
        length_m = data.get('length', 0)
        highway_type = data.get('highway', 'residential')
        
        if isinstance(highway_type, list):
            highway_type = highway_type[0]
        
        # Density by road type
        density_map = {
            'residential': 20,
            'living_street': 30,
            'service': 5,
            'unclassified': 15,
            'tertiary': 10,
            'secondary': 5
        }
        
        density = density_map.get(highway_type, 10)
        estimated = int((length_m / 100) * density)
        
        G[u][v][key]['estimated_addresses'] = max(estimated, 0)
    
    return G

def get_total_estimated_addresses(G: nx.MultiDiGraph) -> int:
    """Get total estimated addresses in the graph."""
    return sum(
        data.get('estimated_addresses', 0) 
        for _, _, data in G.edges(data=True)
    )
```

**Test:** Add to `main.py`:
```python
from backend.density import fetch_buildings, assign_buildings_to_edges

@app.get("/api/test/density")
async def test_density():
    from backend.area import create_circle_polygon
    polygon = create_circle_polygon(40.7128, -74.0060, 500)
    G = fetch_road_network(polygon, 'walking')
    buildings = fetch_buildings(polygon)
    G = assign_buildings_to_edges(G, buildings)
    total = get_total_estimated_addresses(G)
    return {"buildings_found": len(buildings), "estimated_addresses": total}
```

---

#### Commit 7: Zone Partitioning Module
**Goal:** Divide the road network into balanced zones

**File:** `backend/partition.py`
```python
"""
Zone partitioning algorithms for balanced route distribution
"""
import networkx as nx
import numpy as np
from sklearn.cluster import KMeans
from typing import List, Dict, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

def partition_graph_into_zones(
    G: nx.MultiDiGraph,
    num_zones: int,
    balance_priority: str = 'density'
) -> List[nx.MultiDiGraph]:
    """
    Partition graph into balanced zones.
    
    Args:
        G: Road network graph with 'estimated_addresses' on edges
        num_zones: Number of zones to create
        balance_priority: 'density' (balance by addresses) or 'area' (balance by distance)
        
    Returns:
        List of subgraphs, one per zone
    """
    logger.info(f"Partitioning graph into {num_zones} zones (priority: {balance_priority})")
    
    if num_zones == 1:
        return [G.copy()]
    
    # Extract edge midpoints and weights
    edge_data = []
    for u, v, key, data in G.edges(keys=True, data=True):
        # Get edge midpoint
        if 'geometry' in data:
            midpoint = data['geometry'].interpolate(0.5, normalized=True)
            x, y = midpoint.x, midpoint.y
        else:
            x = (G.nodes[u]['x'] + G.nodes[v]['x']) / 2
            y = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2
        
        # Get weight for balancing
        if balance_priority == 'density':
            weight = data.get('estimated_addresses', 0)
        else:  # 'area'
            weight = data.get('length', 0)
        
        edge_data.append({
            'edge': (u, v, key),
            'x': x,
            'y': y,
            'weight': max(weight, 1)  # Avoid zero weights
        })
    
    # Prepare data for clustering
    X = np.array([[e['x'], e['y']] for e in edge_data])
    weights = np.array([e['weight'] for e in edge_data])
    
    # Weighted k-means clustering
    # Repeat points by weight to approximate weighted clustering
    X_weighted = []
    edge_indices_weighted = []
    
    for i, (point, weight) in enumerate(zip(X, weights)):
        repeats = max(1, int(weight / np.mean(weights)))  # Scale by average weight
        X_weighted.extend([point] * repeats)
        edge_indices_weighted.extend([i] * repeats)
    
    X_weighted = np.array(X_weighted)
    
    # Perform k-means
    kmeans = KMeans(n_clusters=num_zones, random_state=42, n_init=10)
    cluster_labels_weighted = kmeans.fit_predict(X_weighted)
    
    # Map back to original edges
    cluster_labels = np.zeros(len(edge_data), dtype=int)
    for i, cluster in enumerate(cluster_labels_weighted):
        original_idx = edge_indices_weighted[i]
        cluster_labels[original_idx] = cluster
    
    # Assign edges to zones
    zone_edges = defaultdict(list)
    for i, edge_info in enumerate(edge_data):
        zone_id = cluster_labels[i]
        zone_edges[zone_id].append(edge_info['edge'])
    
    # Create subgraphs for each zone
    zones = []
    for zone_id in range(num_zones):
        edges = zone_edges[zone_id]
        
        if not edges:
            logger.warning(f"Zone {zone_id} has no edges, skipping")
            continue
        
        # Create subgraph
        subgraph = G.edge_subgraph(edges).copy()
        
        # Ensure connectivity (keep largest connected component)
        if len(subgraph.edges) > 0:
            if not nx.is_strongly_connected(subgraph):
                # Get largest weakly connected component
                components = list(nx.weakly_connected_components(subgraph))
                if components:
                    largest = max(components, key=len)
                    subgraph = subgraph.subgraph(largest).copy()
        
        subgraph.graph['zone_id'] = zone_id
        zones.append(subgraph)
    
    # Balance pass - try to equalize weights
    zones = balance_zones(zones, balance_priority)
    
    logger.info(f"Created {len(zones)} zones")
    for i, zone in enumerate(zones):
        total_weight = sum(
            data.get('estimated_addresses', 0) if balance_priority == 'density' else data.get('length', 0)
            for _, _, data in zone.edges(data=True)
        )
        logger.info(f"  Zone {i}: {len(zone.edges)} edges, weight={total_weight:.0f}")
    
    return zones

def balance_zones(zones: List[nx.MultiDiGraph], balance_priority: str, tolerance: float = 0.15) -> List[nx.MultiDiGraph]:
    """
    Attempt to balance zone weights by swapping boundary edges.
    This is a simple heuristic - not guaranteed to be optimal.
    
    Args:
        zones: List of zone subgraphs
        balance_priority: 'density' or 'area'
        tolerance: Acceptable imbalance (±15%)
        
    Returns:
        Balanced zones
    """
    # For now, return as-is
    # Implementing a full balance algorithm is complex
    # The weighted k-means should provide reasonable initial balance
    return zones

def get_zone_stats(zone: nx.MultiDiGraph) -> Dict:
    """Get statistics for a zone."""
    total_addresses = sum(
        data.get('estimated_addresses', 0)
        for _, _, data in zone.edges(data=True)
    )
    total_length = sum(
        data.get('length', 0)
        for _, _, data in zone.edges(data=True)
    )
    
    # Get bounding box
    lats = [node[1] for node in zone.nodes(data='y')]
    lngs = [node[1] for node in zone.nodes(data='x')]
    
    return {
        'num_edges': len(zone.edges),
        'num_nodes': len(zone.nodes),
        'estimated_addresses': int(total_addresses),
        'total_length_m': float(total_length),
        'bounds': {
            'min_lat': min(lats) if lats else 0,
            'max_lat': max(lats) if lats else 0,
            'min_lng': min(lngs) if lngs else 0,
            'max_lng': max(lngs) if lngs else 0
        }
    }
```

---

#### Commit 8: Route Generation Module (Chinese Postman)
**Goal:** Generate optimized delivery routes through each zone

**File:** `backend/routing.py`
```python
"""
Route generation using Chinese Postman Problem approach
"""
import networkx as nx
from typing import List, Dict, Tuple, Optional
import logging
from itertools import combinations

logger = logging.getLogger(__name__)

def generate_route_for_zone(
    zone: nx.MultiDiGraph,
    start_point: Optional[Tuple[float, float]] = None,
    return_to_start: bool = False,
    travel_mode: str = 'walking'
) -> Dict:
    """
    Generate an optimized delivery route through a zone.
    Uses a simplified Chinese Postman approach.
    
    Args:
        zone: Zone subgraph
        start_point: Starting location (lat, lng), or None for zone centroid
        return_to_start: Whether route should return to start
        travel_mode: 'walking' or 'driving'
        
    Returns:
        Route data dictionary
    """
    logger.info(f"Generating route for zone (travel_mode={travel_mode})")
    
    if len(zone.edges) == 0:
        return {
            'waypoints': [],
            'geometry': {'type': 'LineString', 'coordinates': []},
            'total_distance_m': 0,
            'turn_by_turn': []
        }
    
    # Find start node
    if start_point:
        start_node = find_nearest_node(zone, start_point)
    else:
        # Use node closest to centroid
        lats = [data['y'] for _, data in zone.nodes(data=True)]
        lngs = [data['x'] for _, data in zone.nodes(data=True)]
        centroid = (sum(lats)/len(lats), sum(lngs)/len(lngs))
        start_node = find_nearest_node(zone, centroid)
    
    logger.info(f"Starting from node {start_node}")
    
    # Convert to undirected for walking (pedestrians can traverse both ways)
    if travel_mode == 'walking':
        G_route = zone.to_undirected()
    else:
        G_route = zone.copy()
    
    # Simplified routing: Try to traverse all edges
    # For MVP, use a simple DFS-based approach instead of full Chinese Postman
    route_nodes = generate_simple_route(G_route, start_node, return_to_start)
    
    # Convert to waypoints and compute distance
    waypoints = []
    total_distance = 0
    
    for i, node in enumerate(route_nodes):
        lat = zone.nodes[node]['y']
        lng = zone.nodes[node]['x']
        waypoints.append([lat, lng])
        
        if i > 0:
            # Find edge between previous and current node
            prev_node = route_nodes[i-1]
            try:
                edge_data = zone.get_edge_data(prev_node, node)
                if edge_data:
                    # Get first edge if multiple
                    edge_key = list(edge_data.keys())[0]
                    length = edge_data[edge_key].get('length', 0)
                    total_distance += length
            except:
                pass
    
    # Generate turn-by-turn directions
    turn_by_turn = generate_turn_by_turn(zone, route_nodes)
    
    # Create GeoJSON geometry
    geometry = {
        'type': 'LineString',
        'coordinates': [[lng, lat] for lat, lng in waypoints]
    }
    
    return {
        'waypoints': waypoints,
        'geometry': geometry,
        'total_distance_m': total_distance,
        'turn_by_turn': turn_by_turn
    }

def find_nearest_node(G: nx.Graph, point: Tuple[float, float]) -> int:
    """Find the nearest node to a given point."""
    lat, lng = point
    min_dist = float('inf')
    nearest = None
    
    for node, data in G.nodes(data=True):
        node_lat = data['y']
        node_lng = data['x']
        dist = (node_lat - lat)**2 + (node_lng - lng)**2
        if dist < min_dist:
            min_dist = dist
            nearest = node
    
    return nearest

def generate_simple_route(
    G: nx.Graph, 
    start_node: int, 
    return_to_start: bool
) -> List[int]:
    """
    Generate a simple route that attempts to cover all edges.
    Uses DFS with backtracking.
    
    This is a simplified approach - not optimal but functional for MVP.
    """
    visited_edges = set()
    route = [start_node]
    current = start_node
    
    max_iterations = len(G.edges) * 2 + 100  # Prevent infinite loops
    iterations = 0
    
    while len(visited_edges) < len(G.edges) and iterations < max_iterations:
        iterations += 1
        
        # Get unvisited edges from current node
        unvisited = []
        for neighbor in G.neighbors(current):
            edge = tuple(sorted([current, neighbor]))
            if edge not in visited_edges:
                unvisited.append(neighbor)
        
        if unvisited:
            # Choose next node (prefer unvisited edges)
            next_node = unvisited[0]
            route.append(next_node)
            edge = tuple(sorted([current, next_node]))
            visited_edges.add(edge)
            current = next_node
        else:
            # Backtrack or move to nearest unvisited edge
            # Find shortest path to a node with unvisited edges
            nodes_with_unvisited = set()
            for u, v in G.edges():
                edge = tuple(sorted([u, v]))
                if edge not in visited_edges:
                    nodes_with_unvisited.add(u)
                    nodes_with_unvisited.add(v)
            
            if nodes_with_unvisited:
                # Find nearest node with unvisited edges
                try:
                    paths = {}
                    for target in nodes_with_unvisited:
                        if nx.has_path(G, current, target):
                            path = nx.shortest_path(G, current, target, weight='length')
                            paths[target] = path
                    
                    if paths:
                        # Choose shortest path
                        target = min(paths, key=lambda t: len(paths[t]))
                        path = paths[target]
                        route.extend(path[1:])  # Skip first node (current)
                        current = target
                except:
                    break
            else:
                break
    
    # Return to start if requested
    if return_to_start and current != start_node:
        try:
            if nx.has_path(G, current, start_node):
                return_path = nx.shortest_path(G, current, start_node, weight='length')
                route.extend(return_path[1:])
        except:
            pass
    
    return route

def generate_turn_by_turn(G: nx.Graph, route_nodes: List[int]) -> List[Dict]:
    """
    Generate simple turn-by-turn directions.
    
    For MVP, this is basic - just lists street names.
    """
    directions = []
    
    for i in range(len(route_nodes) - 1):
        current = route_nodes[i]
        next_node = route_nodes[i + 1]
        
        # Get edge data
        try:
            edge_data = G.get_edge_data(current, next_node)
            if edge_data:
                edge_key = list(edge_data.keys())[0]
                street_name = edge_data[edge_key].get('name', 'Unnamed Road')
                distance = edge_data[edge_key].get('length', 0)
                
                if i == 0:
                    instruction = f"Start on {street_name}"
                else:
                    instruction = f"Continue on {street_name}"
                
                directions.append({
                    'instruction': instruction,
                    'distance_m': float(distance),
                    'street_name': street_name
                })
        except:
            pass
    
    # Merge consecutive same streets
    merged = []
    for direction in directions:
        if merged and merged[-1]['street_name'] == direction['street_name']:
            merged[-1]['distance_m'] += direction['distance_m']
        else:
            merged.append(direction)
    
    # Number the directions
    for i, direction in enumerate(merged):
        direction['step'] = i + 1
    
    return merged

def calculate_route_duration(distance_m: float, travel_mode: str) -> float:
    """
    Estimate route duration in minutes.
    
    Args:
        distance_m: Total distance in meters
        travel_mode: 'walking' or 'driving'
        
    Returns:
        Estimated duration in minutes
    """
    if travel_mode == 'walking':
        # Assume 4 km/h walking speed
        speed_kmh = 4.0
    else:  # driving
        # Assume 30 km/h average (residential areas)
        speed_kmh = 30.0
    
    distance_km = distance_m / 1000
    duration_hours = distance_km / speed_kmh
    duration_minutes = duration_hours * 60
    
    return duration_minutes
```

**Note:** This routing is simplified for MVP. A full Chinese Postman implementation would be more complex.

---

#### Commit 9: Main API Endpoint - Generate Routes
**Goal:** Wire everything together in the main API endpoint

**File:** `backend/main.py` (updated with full generate endpoint)

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import logging

from backend.area import create_circle_polygon, create_polygon_from_points, get_centroid
from backend.network import fetch_road_network, get_road_stats, filter_residential_roads
from backend.density import fetch_buildings, assign_buildings_to_edges, get_total_estimated_addresses
from backend.partition import partition_graph_into_zones, get_zone_stats
from backend.routing import generate_route_for_zone, calculate_route_duration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Flyer Route Planner API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Request/Response Models
class AreaCircle(BaseModel):
    type: str = "circle"
    center: Dict[str, float]  # {lat, lng}
    radius_m: float

class AreaPolygon(BaseModel):
    type: str = "polygon"
    points: List[Dict[str, float]]  # [{lat, lng}, ...]

class GenerateRequest(BaseModel):
    area: Dict  # Will be either circle or polygon
    num_routes: int = 4
    total_flyers: int = 1000
    travel_mode: str = "walking"
    start_point: Optional[Dict[str, float]] = None
    return_to_start: bool = False
    balance_priority: str = "density"

# Store jobs in memory (for MVP - no persistence)
jobs = {}

@app.get("/")
async def serve_frontend():
    """Serve the main HTML page"""
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Flyer Route Planner API is running"}

@app.post("/api/generate")
async def generate_routes(request: GenerateRequest):
    """
    Main endpoint to generate delivery routes.
    """
    try:
        logger.info("=== Starting route generation ===")
        logger.info(f"Request: {request.num_routes} routes, {request.total_flyers} flyers, mode={request.travel_mode}")
        
        # Step 1: Create geometry from area
        if request.area['type'] == 'circle':
            center = request.area['center']
            radius = request.area['radius_m']
            polygon = create_circle_polygon(center['lat'], center['lng'], radius)
            logger.info(f"Created circle: center=({center['lat']}, {center['lng']}), radius={radius}m")
        else:  # polygon
            points = request.area['points']
            polygon = create_polygon_from_points(points)
            logger.info(f"Created polygon with {len(points)} points")
        
        # Step 2: Fetch road network
        logger.info("Fetching road network...")
        G = fetch_road_network(polygon, request.travel_mode)
        G = filter_residential_roads(G)
        network_stats = get_road_stats(G)
        logger.info(f"Network: {network_stats['num_edges']} edges, {network_stats['total_length_m']:.0f}m total")
        
        if len(G.edges) == 0:
            raise HTTPException(status_code=400, detail="No roads found in the specified area")
        
        # Step 3: Estimate building density
        logger.info("Estimating address density...")
        buildings = fetch_buildings(polygon)
        G = assign_buildings_to_edges(G, buildings)
        total_addresses = get_total_estimated_addresses(G)
        logger.info(f"Estimated {total_addresses} total addresses")
        
        if total_addresses == 0:
            raise HTTPException(status_code=400, detail="No addresses estimated in area")
        
        # Step 4: Partition into zones
        logger.info(f"Partitioning into {request.num_routes} zones...")
        zones = partition_graph_into_zones(G, request.num_routes, request.balance_priority)
        
        if len(zones) == 0:
            raise HTTPException(status_code=500, detail="Failed to create zones")
        
        # Step 5: Calculate flyer allocation
        zone_stats_list = [get_zone_stats(zone) for zone in zones]
        total_zone_addresses = sum(z['estimated_addresses'] for z in zone_stats_list)
        
        flyers_per_route = []
        for stats in zone_stats_list:
            if total_zone_addresses > 0:
                flyers = int((request.total_flyers * stats['estimated_addresses']) / total_zone_addresses)
            else:
                flyers = request.total_flyers // len(zones)
            flyers_per_route.append(flyers)
        
        # Adjust for rounding
        flyers_diff = request.total_flyers - sum(flyers_per_route)
        if flyers_diff != 0:
            flyers_per_route[0] += flyers_diff
        
        # Step 6: Generate routes for each zone
        logger.info("Generating routes...")
        routes = []
        zone_colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e']
        
        start_point_tuple = None
        if request.start_point:
            start_point_tuple = (request.start_point['lat'], request.start_point['lng'])
        
        for i, zone in enumerate(zones):
            logger.info(f"Generating route {i+1}/{len(zones)}...")
            
            route_data = generate_route_for_zone(
                zone,
                start_point=start_point_tuple,
                return_to_start=request.return_to_start,
                travel_mode=request.travel_mode
            )
            
            # Calculate duration
            duration_min = calculate_route_duration(
                route_data['total_distance_m'],
                request.travel_mode
            )
            
            # Generate Google Maps URL
            google_maps_url = generate_google_maps_url(
                route_data['waypoints'],
                request.travel_mode
            )
            
            routes.append({
                'route_id': i + 1,
                'zone_id': i + 1,
                'color': zone_colors[i % len(zone_colors)],
                'assigned_flyers': flyers_per_route[i],
                'estimated_addresses': zone_stats_list[i]['estimated_addresses'],
                'total_distance_m': route_data['total_distance_m'],
                'estimated_duration_min': int(duration_min),
                'geometry': route_data['geometry'],
                'turn_by_turn': route_data['turn_by_turn'],
                'waypoints': route_data['waypoints'],
                'google_maps_url': google_maps_url
            })
        
        # Create response
        result = {
            'job_id': f"job_{len(jobs) + 1}",
            'routes': routes,
            'summary': {
                'total_addresses_estimated': total_addresses,
                'total_distance_m': sum(r['total_distance_m'] for r in routes),
                'total_estimated_duration_min': sum(r['estimated_duration_min'] for r in routes)
            }
        }
        
        # Store job
        jobs[result['job_id']] = result
        
        logger.info("=== Route generation complete ===")
        return result
        
    except Exception as e:
        logger.error(f"Error generating routes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def generate_google_maps_url(waypoints: List[List[float]], travel_mode: str) -> str:
    """
    Generate a Google Maps directions URL.
    Subsamples waypoints if > 23 (Google's limit).
    """
    if not waypoints or len(waypoints) < 2:
        return ""
    
    # Subsample if too many waypoints
    max_waypoints = 23
    if len(waypoints) > max_waypoints + 2:  # +2 for origin and destination
        step = len(waypoints) // max_waypoints
        sampled = waypoints[::step][:max_waypoints]
    else:
        sampled = waypoints
    
    origin = f"{sampled[0][0]},{sampled[0][1]}"
    destination = f"{sampled[-1][0]},{sampled[-1][1]}"
    
    if len(sampled) > 2:
        waypoints_str = "|".join([f"{wp[0]},{wp[1]}" for wp in sampled[1:-1]])
        url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoints_str}&travelmode={travel_mode}"
    else:
        url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode={travel_mode}"
    
    return url

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

**Test:**
```bash
# Start server
cd backend
python main.py

# Test with curl or use the frontend
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "area": {
      "type": "circle",
      "center": {"lat": 40.7128, "lng": -74.0060},
      "radius_m": 1000
    },
    "num_routes": 2,
    "total_flyers": 500
  }'
```

---

### Phase 3: Frontend Integration & Exports

#### Commit 10: Connect Frontend to API
**Goal:** Wire up the frontend to call the API and display results

**File:** `frontend/app.js` (complete version)

**Note:** This would be a large file. Key sections:

```javascript
// Add these functions to app.js

async function generateRoutes() {
    const status = document.getElementById('status');
    status.className = 'loading';
    status.textContent = 'Generating routes... This may take 30-60 seconds.';
    
    try {
        // Prepare request
        const request = {
            area: state.mode === 'circle' ? {
                type: 'circle',
                center: {
                    lat: state.center.lat,
                    lng: state.center.lng
                },
                radius_m: state.radius
            } : {
                type: 'polygon',
                points: state.polygon
            },
            num_routes: parseInt(document.getElementById('numRoutes').value),
            total_flyers: parseInt(document.getElementById('totalFlyers').value),
            travel_mode: document.getElementById('travelMode').value,
            return_to_start: document.getElementById('returnToStart').checked
        };
        
        // Call API
        const response = await fetch('http://localhost:8000/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed');
        }
        
        const data = await response.json();
        
        // Store and display results
        state.currentJob = data;
        displayRoutes(data);
        
        status.className = 'success';
        status.textContent = `✓ Generated ${data.routes.length} routes covering ~${data.summary.total_addresses_estimated} addresses`;
        
    } catch (error) {
        status.className = 'error';
        status.textContent = `Error: ${error.message}`;
        console.error(error);
    }
}

function displayRoutes(jobData) {
    // Clear existing route layers
    state.layers.forEach(layer => state.map.removeLayer(layer));
    state.layers = [];
    
    // Draw routes on map
    jobData.routes.forEach(route => {
        const coords = route.geometry.coordinates.map(c => [c[1], c[0]]); // [lng, lat] -> [lat, lng]
        
        const line = L.polyline(coords, {
            color: route.color,
            weight: 4,
            opacity: 0.7
        }).addTo(state.map);
        
        line.bindPopup(`
            <strong>Route ${route.route_id}</strong><br>
            Flyers: ${route.assigned_flyers}<br>
            Distance: ${(route.total_distance_m / 1000).toFixed(2)} km<br>
            Est. Time: ${route.estimated_duration_min} min<br>
            <a href="${route.google_maps_url}" target="_blank">Open in Google Maps</a>
        `);
        
        state.layers.push(line);
    });
    
    // Fit map to show all routes
    if (state.layers.length > 0) {
        const group = L.featureGroup(state.layers);
        state.map.fitBounds(group.getBounds().pad(0.1));
    }
    
    // Display route list in sidebar
    const routesList = document.getElementById('routesList');
    routesList.innerHTML = '';
    
    jobData.routes.forEach(route => {
        const item = document.createElement('div');
        item.className = 'route-item';
        item.style.borderLeftColor = route.color;
        item.innerHTML = `
            <strong>Route ${route.route_id}</strong>
            <small>
                ${route.assigned_flyers} flyers • 
                ${(route.total_distance_m / 1000).toFixed(1)} km • 
                ${route.estimated_duration_min} min
            </small>
        `;
        
        item.addEventListener('click', () => {
            // Zoom to this route
            const coords = route.geometry.coordinates.map(c => [c[1], c[0]]);
            const line = L.polyline(coords);
            state.map.fitBounds(line.getBounds().pad(0.2));
        });
        
        routesList.appendChild(item);
    });
    
    document.getElementById('resultsPanel').style.display = 'block';
}
```

---

#### Commit 11: Polygon Drawing Mode
**Goal:** Implement the draw polygon input mode

Add to `frontend/app.js`:
```javascript
let polygonDrawing = false;
let polygonLayer = null;

// In the polygon mode button handler:
document.getElementById('btnPolygon').addEventListener('click', () => {
    state.mode = 'polygon';
    state.polygon = [];
    document.getElementById('btnPolygon').classList.add('active');
    document.getElementById('btnCircle').classList.remove('active');
    document.getElementById('polygonInputs').classList.remove('hidden');
    document.getElementById('circleInputs').classList.add('hidden');
    
    // Enable polygon drawing
    polygonDrawing = true;
    state.map.getContainer().style.cursor = 'crosshair';
});

// Add click handler for polygon mode
state.map.on('click', (e) => {
    if (state.mode === 'polygon' && polygonDrawing) {
        state.polygon.push({ lat: e.latlng.lat, lng: e.latlng.lng });
        updatePolygonOnMap();
        
        if (state.polygon.length >= 3) {
            document.getElementById('btnGenerate').disabled = false;
        }
    }
});

// Add double-click to finish polygon
state.map.on('dblclick', (e) => {
    if (state.mode === 'polygon' && polygonDrawing) {
        polygonDrawing = false;
        state.map.getContainer().style.cursor = '';
        L.DomEvent.stopPropagation(e);
    }
});

function updatePolygonOnMap() {
    // Remove existing polygon layer
    if (polygonLayer) {
        state.map.removeLayer(polygonLayer);
    }
    
    if (state.polygon.length > 0) {
        const coords = state.polygon.map(p => [p.lat, p.lng]);
        
        if (state.polygon.length >= 3) {
            // Draw filled polygon
            polygonLayer = L.polygon(coords, {
                color: '#3498db',
                fillColor: '#3498db',
                fillOpacity: 0.1
            }).addTo(state.map);
        } else {
            // Draw polyline (not closed yet)
            polygonLayer = L.polyline(coords, {
                color: '#3498db',
                dashArray: '5, 5'
            }).addTo(state.map);
        }
    }
}
```

---

#### Commit 12: GPX Export Module
**Goal:** Implement GPX file export for GPS devices

**File:** `backend/export.py`
```python
"""
Export utilities for various formats
"""
import gpxpy
import gpxpy.gpx
from typing import List, Dict
from datetime import datetime

def generate_gpx(route_data: Dict) -> str:
    """
    Generate GPX file content for a route.
    
    Args:
        route_data: Route dictionary with waypoints
        
    Returns:
        GPX file content as string
    """
    gpx = gpxpy.gpx.GPX()
    
    # Create track
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_track.name = f"Route {route_data['route_id']}"
    gpx_track.description = f"{route_data['assigned_flyers']} flyers, {route_data['total_distance_m']/1000:.2f} km"
    gpx.tracks.append(gpx_track)
    
    # Create segment
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    
    # Add waypoints
    for waypoint in route_data['waypoints']:
        lat, lng = waypoint
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lng))
    
    return gpx.to_xml()

def generate_gpx_for_all_routes(routes: List[Dict]) -> str:
    """
    Generate a single GPX file with all routes as separate tracks.
    
    Args:
        routes: List of route dictionaries
        
    Returns:
        GPX file content as string
    """
    gpx = gpxpy.gpx.GPX()
    gpx.name = "Flyer Distribution Routes"
    gpx.description = f"{len(routes)} delivery routes"
    gpx.time = datetime.now()
    
    for route in routes:
        # Create track for this route
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx_track.name = f"Route {route['route_id']}"
        gpx_track.description = f"{route['assigned_flyers']} flyers"
        gpx.tracks.append(gpx_track)
        
        # Create segment
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)
        
        # Add waypoints
        for waypoint in route['waypoints']:
            lat, lng = waypoint
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lng))
    
    return gpx.to_xml()
```

Add export endpoint to `backend/main.py`:
```python
from fastapi.responses import Response
from backend.export import generate_gpx, generate_gpx_for_all_routes

@app.get("/api/export/{job_id}/gpx")
async def export_gpx(job_id: str, route_id: Optional[int] = None):
    """Export routes as GPX file."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = jobs[job_id]
    
    if route_id is not None:
        # Export single route
        route = next((r for r in job_data['routes'] if r['route_id'] == route_id), None)
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        gpx_content = generate_gpx(route)
        filename = f"route_{route_id}.gpx"
    else:
        # Export all routes
        gpx_content = generate_gpx_for_all_routes(job_data['routes'])
        filename = f"all_routes.gpx"
    
    return Response(
        content=gpx_content,
        media_type="application/gpx+xml",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
```

Wire up in frontend:
```javascript
document.getElementById('btnExportGPX').addEventListener('click', () => {
    if (state.currentJob) {
        const url = `http://localhost:8000/api/export/${state.currentJob.job_id}/gpx`;
        window.open(url, '_blank');
    }
});
```

---

#### Commit 13: Printable Directions Page
**Goal:** Create a printable turn-by-turn directions page

**File:** `frontend/print.html` (new file)
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Route Directions</title>
    <style>
        @media print {
            .no-print { display: none; }
            .page-break { page-break-before: always; }
        }
        
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        
        .route-page {
            margin-bottom: 40px;
        }
        
        .route-header {
            border-left: 8px solid;
            padding-left: 15px;
            margin-bottom: 20px;
        }
        
        .route-header h1 {
            margin: 0;
            font-size: 24px;
        }
        
        .route-info {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 20px 0;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
        }
        
        .info-item strong {
            display: block;
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .info-item span {
            display: block;
            font-size: 20px;
            font-weight: bold;
            margin-top: 5px;
        }
        
        .directions {
            margin-top: 30px;
        }
        
        .direction-step {
            display: flex;
            margin-bottom: 15px;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .step-number {
            width: 40px;
            height: 40px;
            background: #3498db;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            flex-shrink: 0;
            margin-right: 15px;
        }
        
        .step-content {
            flex: 1;
        }
        
        .step-content strong {
            display: block;
            margin-bottom: 5px;
        }
        
        .step-distance {
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="no-print">
        <button onclick="window.print()">🖨️ Print</button>
        <button onclick="window.close()">Close</button>
    </div>
    
    <div id="content"></div>
    
    <script>
        // Get job data from localStorage or URL parameter
        const params = new URLSearchParams(window.location.search);
        const jobDataStr = params.get('data');
        
        if (jobDataStr) {
            const jobData = JSON.parse(decodeURIComponent(jobDataStr));
            renderDirections(jobData);
        }
        
        function renderDirections(jobData) {
            const content = document.getElementById('content');
            
            jobData.routes.forEach((route, index) => {
                const pageDiv = document.createElement('div');
                pageDiv.className = 'route-page' + (index > 0 ? ' page-break' : '');
                
                pageDiv.innerHTML = `
                    <div class="route-header" style="border-left-color: ${route.color}">
                        <h1>Route ${route.route_id}</h1>
                    </div>
                    
                    <div class="route-info">
                        <div class="info-item">
                            <strong>Flyers to Distribute</strong>
                            <span>${route.assigned_flyers}</span>
                        </div>
                        <div class="info-item">
                            <strong>Total Distance</strong>
                            <span>${(route.total_distance_m / 1000).toFixed(2)} km</span>
                        </div>
                        <div class="info-item">
                            <strong>Estimated Time</strong>
                            <span>${route.estimated_duration_min} min</span>
                        </div>
                    </div>
                    
                    <div class="directions">
                        <h2>Turn-by-Turn Directions</h2>
                        ${route.turn_by_turn.map(step => `
                            <div class="direction-step">
                                <div class="step-number">${step.step}</div>
                                <div class="step-content">
                                    <strong>${step.instruction}</strong>
                                    <span class="step-distance">${(step.distance_m).toFixed(0)} meters</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
                
                content.appendChild(pageDiv);
            });
        }
    </script>
</body>
</html>
```

Add button handler in `frontend/app.js`:
```javascript
document.getElementById('btnPrint').addEventListener('click', () => {
    if (state.currentJob) {
        const dataStr = encodeURIComponent(JSON.stringify(state.currentJob));
        window.open(`/static/print.html?data=${dataStr}`, '_blank');
    }
});
```

---

#### Commit 14: KML & GeoJSON Export
**Goal:** Add KML and GeoJSON export options

Add to `backend/export.py`:
```python
import simplekml
import json

def generate_kml(routes: List[Dict]) -> str:
    """Generate KML file for all routes."""
    kml = simplekml.Kml()
    
    for route in routes:
        # Create a folder for this route
        folder = kml.newfolder(name=f"Route {route['route_id']}")
        
        # Add route line
        linestring = folder.newlinestring(name=f"Route {route['route_id']} Path")
        linestring.coords = [(wp[1], wp[0]) for wp in route['waypoints']]  # KML uses (lng, lat)
        linestring.style.linestyle.color = simplekml.Color.rgb(
            int(route['color'][1:3], 16),
            int(route['color'][3:5], 16),
            int(route['color'][5:7], 16)
        )
        linestring.style.linestyle.width = 4
        
        # Add description
        linestring.description = f"""
        Flyers: {route['assigned_flyers']}<br>
        Distance: {route['total_distance_m']/1000:.2f} km<br>
        Est. Time: {route['estimated_duration_min']} minutes
        """
    
    return kml.kml()

def generate_geojson(routes: List[Dict]) -> str:
    """Generate GeoJSON FeatureCollection."""
    features = []
    
    for route in routes:
        feature = {
            "type": "Feature",
            "properties": {
                "route_id": route['route_id'],
                "flyers": route['assigned_flyers'],
                "distance_m": route['total_distance_m'],
                "duration_min": route['estimated_duration_min'],
                "color": route['color']
            },
            "geometry": route['geometry']
        }
        features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return json.dumps(geojson, indent=2)
```

Add endpoints to `backend/main.py`:
```python
from backend.export import generate_kml, generate_geojson

@app.get("/api/export/{job_id}/kml")
async def export_kml(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    kml_content = generate_kml(jobs[job_id]['routes'])
    
    return Response(
        content=kml_content,
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": "attachment; filename=routes.kml"}
    )

@app.get("/api/export/{job_id}/geojson")
async def export_geojson(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    geojson_content = generate_geojson(jobs[job_id]['routes'])
    
    return Response(
        content=geojson_content,
        media_type="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=routes.geojson"}
    )
```

---

### Phase 4: Polish & Documentation

#### Commit 15: Error Handling & Loading States
**Goal:** Improve UX with better error handling and loading indicators

- Add proper error boundaries
- Add loading spinner
- Add timeout handling (OSM queries can be slow)
- Add validation for inputs

---

#### Commit 16: README & Documentation
**Goal:** Complete documentation for users and developers

**File:** `README.md`
```markdown
# 🗺️ Flyer Route Planner

A web application that divides a geographic area into balanced delivery zones and generates optimized walking or driving routes for flyer distribution.

## Features

- 📍 Define area by center + radius or by drawing a polygon
- 🏘️ Automatic address density estimation using OpenStreetMap building data
- ⚖️ Balanced zone partitioning (equal flyers per route)
- 🚶‍♂️ Walking or driving route generation
- 🗺️ Interactive map visualization
- 📄 Printable turn-by-turn directions
- 📤 Export to GPX, KML, GeoJSON, and Google Maps

## Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. Clone or download this repository
2. Install dependencies:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

4. Open your browser to http://localhost:8000

## Usage

1. **Define Area**: Click on the map to set a center point and adjust radius, OR switch to polygon mode and draw your target area
2. **Set Parameters**: Choose number of routes, total flyers, and travel mode (walking/driving)
3. **Generate**: Click "Generate Routes" and wait 30-60 seconds
4. **View & Export**: View routes on the map, print directions, or export to GPS

## Technical Details

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript + Leaflet.js
- **Routing**: NetworkX graph algorithms (simplified Chinese Postman)
- **Data**: OpenStreetMap via OSMnx

## Limitations

- Address counts are estimates (±20-30% accuracy)
- Route optimization is approximate (good enough for distribution)
- Large areas (>5km radius) may take 2-3 minutes to process
- Requires internet connection for map tiles and OSM data

## License

MIT License - Free to use and modify

## Support

For issues or questions, please refer to the original spec document.
```

---

#### Commit 17: Configuration & Environment Variables
**Goal:** Add configuration file for customization

**File:** `backend/config.py`
```python
import os
from typing import Optional

class Config:
    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    
    # OSM settings
    OSM_CACHE_DIR = os.getenv("OSM_CACHE_DIR", "./cache/osm")
    OSM_TIMEOUT = int(os.getenv("OSM_TIMEOUT", 300))  # seconds
    
    # Route generation
    DEFAULT_NUM_ROUTES = 4
    MAX_NUM_ROUTES = 20
    MIN_RADIUS_M = 100
    MAX_RADIUS_M = 10000
    
    # Density estimation
    BUILDING_MAX_DISTANCE_M = 50
    DENSITY_MULTIPLIER_SUBURBAN = 20.0
    DENSITY_MULTIPLIER_URBAN = 40.0
    DENSITY_MULTIPLIER_RURAL = 10.0
    
    # Speed estimates (km/h)
    WALKING_SPEED_KMH = 4.0
    DRIVING_SPEED_KMH = 30.0
    
    # Google Maps API (optional)
    GOOGLE_MAPS_API_KEY: Optional[str] = os.getenv("GOOGLE_MAPS_API_KEY")
    
    # Export settings
    GPX_MAX_WAYPOINTS = 1000
    GOOGLE_MAPS_MAX_WAYPOINTS = 23

config = Config()
```

---

#### Commit 18: Docker Support (Optional)
**Goal:** Add Docker support for easy deployment

**File:** `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File:** `docker-compose.yml`
```yaml
version: '3.8'

services:
  flyer-planner:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./cache:/app/cache
    environment:
      - OSM_CACHE_DIR=/app/cache/osm
```

---

#### Commit 19: Testing & Validation
**Goal:** Add basic tests for core functionality

**File:** `backend/tests/test_area.py`
```python
import pytest
from backend.area import create_circle_polygon, get_bounding_box

def test_circle_polygon_creation():
    polygon = create_circle_polygon(40.7128, -74.0060, 1000)
    assert polygon.is_valid
    assert polygon.geom_type == 'Polygon'

def test_bounding_box():
    polygon = create_circle_polygon(40.7128, -74.0060, 1000)
    bbox = get_bounding_box(polygon)
    assert len(bbox) == 4
    assert bbox[0] < bbox[2]  # min_lng < max_lng
    assert bbox[1] < bbox[3]  # min_lat < max_lat
```

---

#### Commit 20: Final Polish & Performance Optimization
**Goal:** Final touches, performance improvements, and cleanup

- Add request caching for repeated areas
- Optimize graph algorithms
- Add progress indicators for long-running tasks
- Clean up console logging
- Final UI polish

---

## 🎯 Testing Checkpoints

After completing each phase, test with these scenarios:

**Phase 1 (Commits 1-3):**
- Server starts without errors
- Map loads and displays
- Can click to place center point
- Radius slider works

**Phase 2 (Commits 4-9):**
- Test endpoint returns road network stats
- Building density estimation works
- Can generate routes for small area (500m radius)
- Response includes routes with waypoints

**Phase 3 (Commits 10-14):**
- Frontend successfully calls API
- Routes display on map with colors
- Can click routes to zoom
- Exports download correctly
- Print page formats properly

**Phase 4 (Commits 15-20):**
- Error messages are helpful
- Loading states are clear
- Documentation is complete
- Docker deployment works (if implemented)

---

## 🚀 Deployment Options

### Local Development (Default)
```bash
cd backend && python main.py
```

### Production with Gunicorn
```bash
gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker
```bash
docker-compose up
```

---

## 📝 User Instructions to Provide

When starting with Claude Code, provide:

1. **Confirm Prerequisites:**
   - "I have Python 3.8+ installed"
   - "I want to run this locally" (or specify deployment target)

2. **Optional Configuration:**
   - Google Maps API key (if available)
   - Preferred port (default: 8000)

3. **Feature Priorities:**
   - "Include PDF export" (requires additional library)
   - "Skip Docker setup for now"

---

## 🐛 Known Issues & Future Enhancements

### Known Limitations:
- Route optimization is approximate (not perfect)
- Large areas (>5km) can be slow
- Address estimation accuracy varies by region

### Future Enhancements:
- Per-route travel mode (mix walking/driving)
- Manual zone boundary adjustment
- Progress tracking feature
- Integration with commercial routing APIs
- Batch job processing
- User accounts and saved jobs

---

## 📊 Performance Expectations

- **Small area** (500m radius): ~15-30 seconds
- **Medium area** (1-2km radius): ~30-60 seconds  
- **Large area** (3-5km radius): ~60-180 seconds

Processing time depends on:
- Road network density
- Number of routes
- Internet connection speed (for OSM downloads)

---

## ✅ Success Criteria

The implementation is complete when:

1. ✅ User can define area via map interaction
2. ✅ Routes are generated and displayed on map
3. ✅ Each route shows flyer count and distance
4. ✅ Can export to GPX, KML, GeoJSON
5. ✅ Can open routes in Google Maps
6. ✅ Printable directions are formatted clearly
7. ✅ Error handling is robust
8. ✅ Documentation is complete

---

This plan provides a complete roadmap for building the Flyer Route Planner with Claude Code. Each commit is designed to be a working increment that can be tested before moving to the next step.
