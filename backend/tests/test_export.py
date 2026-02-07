import pytest
from backend.export import (
    generate_gpx,
    generate_gpx_for_all_routes,
    generate_kml,
    generate_geojson,
    generate_google_maps_url,
)
import json


SAMPLE_ROUTE = {
    "route_id": 1,
    "assigned_flyers": 250,
    "total_distance_m": 5200,
    "estimated_duration_min": 65,
    "color": "#e74c3c",
    "waypoints": [[40.7128, -74.0060], [40.7130, -74.0055], [40.7135, -74.0050]],
    "geometry": {
        "type": "LineString",
        "coordinates": [[-74.0060, 40.7128], [-74.0055, 40.7130], [-74.0050, 40.7135]],
    },
}


def test_gpx_generation():
    gpx = generate_gpx(SAMPLE_ROUTE)
    assert "<?xml" in gpx
    assert "Route 1" in gpx
    assert "gpx" in gpx


def test_gpx_all_routes():
    routes = [SAMPLE_ROUTE, {**SAMPLE_ROUTE, "route_id": 2}]
    gpx = generate_gpx_for_all_routes(routes)
    assert "Route 1" in gpx
    assert "Route 2" in gpx


def test_kml_generation():
    routes = [SAMPLE_ROUTE]
    kml = generate_kml(routes)
    assert "kml" in kml.lower()
    assert "Route 1" in kml


def test_geojson_generation():
    routes = [SAMPLE_ROUTE]
    geojson_str = generate_geojson(routes)
    data = json.loads(geojson_str)
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    assert data["features"][0]["properties"]["route_id"] == 1


def test_google_maps_url():
    waypoints = [[40.7128, -74.0060], [40.7130, -74.0055], [40.7135, -74.0050]]
    url = generate_google_maps_url(waypoints, "walking")
    assert "google.com/maps/dir" in url
    assert "walking" in url


def test_google_maps_url_empty():
    url = generate_google_maps_url([], "walking")
    assert url == ""


def test_google_maps_url_two_points():
    waypoints = [[40.7128, -74.0060], [40.7135, -74.0050]]
    url = generate_google_maps_url(waypoints, "driving")
    assert "google.com/maps/dir" in url
    assert "driving" in url
