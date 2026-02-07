"""
Geometry and area handling utilities.
"""
from typing import Dict, List, Tuple
from shapely.geometry import Point, Polygon
import math


def create_circle_polygon(
    center_lat: float, center_lng: float, radius_m: float, num_points: int = 64
) -> Polygon:
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
    lat_deg_per_m = 1 / 111320
    lng_deg_per_m = 1 / (111320 * math.cos(math.radians(center_lat)))

    points = []
    for i in range(num_points):
        angle = (2 * math.pi * i) / num_points
        lat = center_lat + (radius_m * math.sin(angle) * lat_deg_per_m)
        lng = center_lng + (radius_m * math.cos(angle) * lng_deg_per_m)
        points.append((lng, lat))  # Shapely uses (x, y) = (lng, lat)

    return Polygon(points)


def create_polygon_from_points(points: List[Dict[str, float]]) -> Polygon:
    """
    Create a polygon from a list of lat/lng points.

    Args:
        points: List of dicts with 'lat' and 'lng' keys

    Returns:
        Shapely Polygon
    """
    coords = [(p["lng"], p["lat"]) for p in points]
    return Polygon(coords)


def get_bounding_box(geometry: Polygon) -> Tuple[float, float, float, float]:
    """
    Get bounding box of geometry.

    Returns:
        (min_lng, min_lat, max_lng, max_lat)
    """
    return geometry.bounds


def get_centroid(geometry: Polygon) -> Tuple[float, float]:
    """
    Get centroid of geometry.

    Returns:
        (lat, lng)
    """
    centroid = geometry.centroid
    return (centroid.y, centroid.x)
