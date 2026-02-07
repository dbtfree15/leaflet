"""
Flyer Route Planner — FastAPI backend.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import logging
import uuid

from backend.area import create_circle_polygon, create_polygon_from_points
from backend.network import fetch_road_network, get_road_stats, filter_residential_roads
from backend.density import (
    fetch_buildings,
    assign_buildings_to_edges,
    get_total_estimated_addresses,
)
from backend.partition import partition_graph_into_zones, get_zone_stats
from backend.routing import generate_route_for_zone, calculate_route_duration
from backend.export import (
    generate_gpx,
    generate_gpx_for_all_routes,
    generate_kml,
    generate_geojson,
    generate_google_maps_url,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Leaflet — Flyer Route Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
frontend_dir = os.path.abspath(frontend_dir)


# --- Request / Response Models ---


class GenerateRequest(BaseModel):
    area: Dict
    num_routes: int = 4
    total_flyers: int = 1000
    travel_mode: str = "walking"
    start_point: Optional[Dict[str, float]] = None
    return_to_start: bool = False
    balance_priority: str = "density"


# In-memory job store (MVP — no persistence)
jobs: Dict[str, Dict] = {}


# --- Routes ---


@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(frontend_dir, "index.html"))


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Leaflet API is running"}


@app.post("/api/generate")
async def generate_routes(request: GenerateRequest):
    """Main endpoint to generate delivery routes."""
    try:
        logger.info("=== Starting route generation ===")
        logger.info(
            f"Request: {request.num_routes} routes, "
            f"{request.total_flyers} flyers, mode={request.travel_mode}"
        )

        # Validate
        if request.num_routes < 1 or request.num_routes > 20:
            raise HTTPException(
                status_code=400, detail="num_routes must be between 1 and 20"
            )

        # Step 1: Create geometry
        if request.area.get("type") == "circle":
            center = request.area["center"]
            radius = request.area["radius_m"]
            polygon = create_circle_polygon(center["lat"], center["lng"], radius)
            logger.info(
                f"Circle area: center=({center['lat']:.5f}, {center['lng']:.5f}), "
                f"radius={radius}m"
            )
        elif request.area.get("type") == "polygon":
            points = request.area["points"]
            if len(points) < 3:
                raise HTTPException(
                    status_code=400, detail="Polygon must have at least 3 points"
                )
            polygon = create_polygon_from_points(points)
            logger.info(f"Polygon area with {len(points)} vertices")
        else:
            raise HTTPException(
                status_code=400, detail="area.type must be 'circle' or 'polygon'"
            )

        # Step 2: Fetch road network
        logger.info("Fetching road network...")
        G = fetch_road_network(polygon, request.travel_mode)
        G = filter_residential_roads(G)
        stats = get_road_stats(G)
        logger.info(
            f"Network: {stats['num_edges']} edges, "
            f"{stats['total_length_m']:.0f}m total"
        )

        if len(G.edges) == 0:
            raise HTTPException(
                status_code=400,
                detail="No roads found in the specified area. Try a larger area.",
            )

        # Step 3: Estimate building density
        logger.info("Estimating address density...")
        buildings = fetch_buildings(polygon)
        G = assign_buildings_to_edges(G, buildings)
        total_addresses = get_total_estimated_addresses(G)
        logger.info(f"Estimated {total_addresses} total addresses")

        if total_addresses == 0:
            logger.warning("No addresses found, falling back to road-length estimate")
            from backend.density import estimate_from_road_length

            G = estimate_from_road_length(G)
            total_addresses = get_total_estimated_addresses(G)

        # Step 4: Partition into zones
        actual_zones = min(request.num_routes, len(G.edges))
        logger.info(f"Partitioning into {actual_zones} zones...")
        zones = partition_graph_into_zones(G, actual_zones, request.balance_priority)

        if len(zones) == 0:
            raise HTTPException(status_code=500, detail="Failed to create zones")

        # Step 5: Calculate flyer allocation
        zone_stats_list = [get_zone_stats(zone) for zone in zones]
        total_zone_addresses = sum(z["estimated_addresses"] for z in zone_stats_list)

        flyers_per_route = []
        for zs in zone_stats_list:
            if total_zone_addresses > 0:
                flyers = int(
                    (request.total_flyers * zs["estimated_addresses"])
                    / total_zone_addresses
                )
            else:
                flyers = request.total_flyers // len(zones)
            flyers_per_route.append(flyers)

        # Fix rounding
        diff = request.total_flyers - sum(flyers_per_route)
        if diff != 0:
            flyers_per_route[0] += diff

        # Step 6: Generate routes
        logger.info("Generating routes per zone...")
        routes = []
        zone_colors = [
            "#e74c3c",
            "#3498db",
            "#2ecc71",
            "#f39c12",
            "#9b59b6",
            "#1abc9c",
            "#e67e22",
            "#34495e",
            "#c0392b",
            "#2980b9",
            "#27ae60",
            "#d35400",
            "#8e44ad",
            "#16a085",
            "#f1c40f",
            "#7f8c8d",
            "#2c3e50",
            "#d63031",
            "#0984e3",
            "#00b894",
        ]

        start_pt = None
        if request.start_point:
            start_pt = (request.start_point["lat"], request.start_point["lng"])

        for i, zone in enumerate(zones):
            logger.info(f"  Route {i+1}/{len(zones)}...")

            route_data = generate_route_for_zone(
                zone,
                start_point=start_pt,
                return_to_start=request.return_to_start,
                travel_mode=request.travel_mode,
            )

            duration_min = calculate_route_duration(
                route_data["total_distance_m"], request.travel_mode
            )

            gmaps_url = generate_google_maps_url(
                route_data["waypoints"], request.travel_mode
            )

            routes.append(
                {
                    "route_id": i + 1,
                    "zone_id": i + 1,
                    "color": zone_colors[i % len(zone_colors)],
                    "assigned_flyers": flyers_per_route[i],
                    "estimated_addresses": zone_stats_list[i]["estimated_addresses"],
                    "total_distance_m": route_data["total_distance_m"],
                    "estimated_duration_min": max(1, int(duration_min)),
                    "geometry": route_data["geometry"],
                    "turn_by_turn": route_data["turn_by_turn"],
                    "waypoints": route_data["waypoints"],
                    "google_maps_url": gmaps_url,
                }
            )

        job_id = f"job_{uuid.uuid4().hex[:8]}"
        result = {
            "job_id": job_id,
            "routes": routes,
            "summary": {
                "total_addresses_estimated": total_addresses,
                "total_distance_m": sum(r["total_distance_m"] for r in routes),
                "total_estimated_duration_min": sum(
                    r["estimated_duration_min"] for r in routes
                ),
            },
        }

        jobs[job_id] = result

        logger.info("=== Route generation complete ===")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating routes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- Export Endpoints ---


@app.get("/api/export/{job_id}/gpx")
async def export_gpx(job_id: str, route_id: Optional[int] = None):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_data = jobs[job_id]

    if route_id is not None:
        route = next(
            (r for r in job_data["routes"] if r["route_id"] == route_id), None
        )
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        gpx_content = generate_gpx(route)
        filename = f"route_{route_id}.gpx"
    else:
        gpx_content = generate_gpx_for_all_routes(job_data["routes"])
        filename = "all_routes.gpx"

    return Response(
        content=gpx_content,
        media_type="application/gpx+xml",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/export/{job_id}/kml")
async def export_kml(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    kml_content = generate_kml(jobs[job_id]["routes"])

    return Response(
        content=kml_content,
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": "attachment; filename=routes.kml"},
    )


@app.get("/api/export/{job_id}/geojson")
async def export_geojson(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    geojson_content = generate_geojson(jobs[job_id]["routes"])

    return Response(
        content=geojson_content,
        media_type="application/geo+json",
        headers={"Content-Disposition": "attachment; filename=routes.geojson"},
    )


# Mount static files AFTER API routes so /api/* takes priority
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
