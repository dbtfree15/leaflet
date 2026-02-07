"""
Export utilities for GPX, KML, GeoJSON, and Google Maps URL generation.
"""
import gpxpy
import gpxpy.gpx
import simplekml
import json
from typing import List, Dict
from datetime import datetime


def generate_gpx(route_data: Dict) -> str:
    """Generate GPX file content for a single route."""
    gpx = gpxpy.gpx.GPX()

    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_track.name = f"Route {route_data['route_id']}"
    gpx_track.description = (
        f"{route_data['assigned_flyers']} flyers, "
        f"{route_data['total_distance_m']/1000:.2f} km"
    )
    gpx.tracks.append(gpx_track)

    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for waypoint in route_data["waypoints"]:
        lat, lng = waypoint
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lng))

    return gpx.to_xml()


def generate_gpx_for_all_routes(routes: List[Dict]) -> str:
    """Generate a single GPX file with all routes as separate tracks."""
    gpx = gpxpy.gpx.GPX()
    gpx.name = "Flyer Distribution Routes"
    gpx.description = f"{len(routes)} delivery routes"
    gpx.time = datetime.now()

    for route in routes:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx_track.name = f"Route {route['route_id']}"
        gpx_track.description = f"{route['assigned_flyers']} flyers"
        gpx.tracks.append(gpx_track)

        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        for waypoint in route["waypoints"]:
            lat, lng = waypoint
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lng))

    return gpx.to_xml()


def generate_kml(routes: List[Dict]) -> str:
    """Generate KML file for all routes."""
    kml = simplekml.Kml()

    for route in routes:
        folder = kml.newfolder(name=f"Route {route['route_id']}")

        linestring = folder.newlinestring(name=f"Route {route['route_id']} Path")
        linestring.coords = [(wp[1], wp[0]) for wp in route["waypoints"]]

        color_hex = route["color"].lstrip("#")
        linestring.style.linestyle.color = simplekml.Color.rgb(
            int(color_hex[0:2], 16),
            int(color_hex[2:4], 16),
            int(color_hex[4:6], 16),
        )
        linestring.style.linestyle.width = 4

        linestring.description = (
            f"Flyers: {route['assigned_flyers']}<br>"
            f"Distance: {route['total_distance_m']/1000:.2f} km<br>"
            f"Est. Time: {route['estimated_duration_min']} minutes"
        )

    return kml.kml()


def generate_geojson(routes: List[Dict]) -> str:
    """Generate GeoJSON FeatureCollection."""
    features = []

    for route in routes:
        feature = {
            "type": "Feature",
            "properties": {
                "route_id": route["route_id"],
                "flyers": route["assigned_flyers"],
                "distance_m": route["total_distance_m"],
                "duration_min": route["estimated_duration_min"],
                "color": route["color"],
            },
            "geometry": route["geometry"],
        }
        features.append(feature)

    geojson = {"type": "FeatureCollection", "features": features}

    return json.dumps(geojson, indent=2)


def generate_google_maps_url(
    waypoints: List[List[float]], travel_mode: str
) -> str:
    """
    Generate a Google Maps directions URL.
    Subsamples waypoints if > 23 (Google's limit).
    """
    if not waypoints or len(waypoints) < 2:
        return ""

    max_wp = 23
    if len(waypoints) > max_wp + 2:
        step = len(waypoints) // max_wp
        sampled = waypoints[::step][:max_wp]
    else:
        sampled = waypoints

    origin = f"{sampled[0][0]},{sampled[0][1]}"
    destination = f"{sampled[-1][0]},{sampled[-1][1]}"

    mode = "walking" if travel_mode == "walking" else "driving"

    if len(sampled) > 2:
        waypoints_str = "|".join(
            [f"{wp[0]},{wp[1]}" for wp in sampled[1:-1]]
        )
        return (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={origin}&destination={destination}"
            f"&waypoints={waypoints_str}&travelmode={mode}"
        )
    else:
        return (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={origin}&destination={destination}"
            f"&travelmode={mode}"
        )
