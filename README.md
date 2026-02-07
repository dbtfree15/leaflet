# Leaflet — Flyer Route Planner

A web application that divides a geographic area into balanced delivery zones and generates optimized walking or driving routes for flyer distribution.

## Features

- **Area Definition**: Click a center + radius or draw a polygon on an interactive map
- **Address Density Estimation**: Uses OpenStreetMap building data to estimate addresses per road segment
- **Balanced Zone Partitioning**: Splits area into zones with equal flyer counts (weighted by address density)
- **Route Generation**: Optimized delivery routes per zone using graph traversal algorithms
- **Multiple Exports**: GPX, KML, GeoJSON, Google Maps links
- **Printable Directions**: Turn-by-turn directions formatted for printing

## Quick Start (Local Development)

### Prerequisites
- Python 3.8+
- pip

### Install & Run

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000

## Deploy on Synology NAS (Portainer)

### Option 1: Docker Compose via Portainer

1. In Portainer, go to **Stacks** > **Add Stack**
2. Name the stack `leaflet`
3. Upload or paste the `docker-compose.yml` contents
4. Click **Deploy the stack**
5. Access the app at `http://<NAS_IP>:8000`

### Option 2: Build & Run Manually

```bash
# On your NAS or via SSH
git clone <this-repo> leaflet
cd leaflet
docker build -t leaflet .
docker run -d --name leaflet -p 8000:8000 -v leaflet_cache:/app/cache --restart unless-stopped leaflet
```

### Option 3: Portainer Git Deploy

1. In Portainer, go to **Stacks** > **Add Stack**
2. Select **Repository**
3. Enter the git repository URL
4. Set compose path to `docker-compose.yml`
5. Deploy

## Usage

1. **Define Area**: Click on the map to set a center point and adjust the radius slider, or switch to polygon mode and click to draw vertices (double-click to finish)
2. **Set Parameters**: Choose number of routes, total flyers, walking/driving mode
3. **Generate**: Click "Generate Routes" — processing takes 30-60 seconds depending on area size
4. **View Results**: Routes appear on the map color-coded by zone. Click a route for details.
5. **Export**: Download GPX for GPS devices, KML for Google Earth, GeoJSON for GIS tools, or open directly in Google Maps

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/generate` | Generate routes |
| GET | `/api/export/{job_id}/gpx` | Export as GPX |
| GET | `/api/export/{job_id}/kml` | Export as KML |
| GET | `/api/export/{job_id}/geojson` | Export as GeoJSON |

## Tech Stack

- **Backend**: Python / FastAPI
- **Frontend**: Vanilla JavaScript + Leaflet.js
- **Data**: OpenStreetMap via osmnx
- **Algorithms**: NetworkX (graph partitioning, route generation)
- **Deployment**: Docker

## Limitations

- Address counts are estimates (±20-30% accuracy depending on OSM data quality in the area)
- Route optimization is approximate — good enough for flyer distribution
- Large areas (>5km radius) may take 2-3 minutes to process
- Requires internet connection for OSM data fetching and map tiles
