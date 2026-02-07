import os
from typing import Optional


class Config:
    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))

    # OSM settings
    OSM_CACHE_DIR = os.getenv("OSM_CACHE_DIR", "./cache/osm")
    OSM_TIMEOUT = int(os.getenv("OSM_TIMEOUT", 300))

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
