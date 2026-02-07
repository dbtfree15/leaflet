import pytest
from backend.area import (
    create_circle_polygon,
    create_polygon_from_points,
    get_bounding_box,
    get_centroid,
)


def test_circle_polygon_creation():
    polygon = create_circle_polygon(40.7128, -74.0060, 1000)
    assert polygon.is_valid
    assert polygon.geom_type == "Polygon"


def test_circle_polygon_contains_center():
    from shapely.geometry import Point

    polygon = create_circle_polygon(40.7128, -74.0060, 1000)
    center = Point(-74.0060, 40.7128)  # (lng, lat)
    assert polygon.contains(center)


def test_bounding_box():
    polygon = create_circle_polygon(40.7128, -74.0060, 1000)
    bbox = get_bounding_box(polygon)
    assert len(bbox) == 4
    assert bbox[0] < bbox[2]  # min_lng < max_lng
    assert bbox[1] < bbox[3]  # min_lat < max_lat


def test_centroid():
    polygon = create_circle_polygon(40.7128, -74.0060, 1000)
    lat, lng = get_centroid(polygon)
    assert abs(lat - 40.7128) < 0.001
    assert abs(lng - (-74.0060)) < 0.001


def test_polygon_from_points():
    points = [
        {"lat": 40.71, "lng": -74.01},
        {"lat": 40.72, "lng": -74.01},
        {"lat": 40.72, "lng": -74.00},
        {"lat": 40.71, "lng": -74.00},
    ]
    polygon = create_polygon_from_points(points)
    assert polygon.is_valid
    assert polygon.geom_type == "Polygon"


def test_small_radius():
    polygon = create_circle_polygon(40.7128, -74.0060, 100)
    assert polygon.is_valid
    assert polygon.area > 0


def test_large_radius():
    polygon = create_circle_polygon(40.7128, -74.0060, 5000)
    assert polygon.is_valid
    assert polygon.area > 0
