"""
OpenStreetMap network fetching and graph building.
"""
import osmnx as ox
import networkx as nx
from shapely.geometry import Polygon
from typing import Dict
import logging

logger = logging.getLogger(__name__)

ox.settings.use_cache = True
ox.settings.log_console = True


def fetch_road_network(polygon: Polygon, travel_mode: str = "walk") -> nx.MultiDiGraph:
    """
    Fetch road network from OpenStreetMap within the given polygon.

    Args:
        polygon: Shapely Polygon defining the area
        travel_mode: 'walk' or 'drive'

    Returns:
        NetworkX MultiDiGraph with road network
    """
    logger.info(f"Fetching {travel_mode} network from OSM...")

    network_type = "walk" if travel_mode == "walking" else "drive"

    G = ox.graph_from_polygon(
        polygon, network_type=network_type, simplify=True, retain_all=False
    )

    logger.info(f"Network fetched: {len(G.nodes)} nodes, {len(G.edges)} edges")

    G = ox.add_edge_lengths(G)

    for u, v, key, data in G.edges(keys=True, data=True):
        if "name" not in data:
            data["name"] = "Unnamed Road"
        if "highway" not in data:
            data["highway"] = "unclassified"

    return G


def get_road_stats(G: nx.MultiDiGraph) -> Dict:
    """Get statistics about the road network."""
    total_length = sum(data.get("length", 0) for _, _, data in G.edges(data=True))

    road_types = {}
    for _, _, data in G.edges(data=True):
        highway_type = data.get("highway", "unknown")
        if isinstance(highway_type, list):
            highway_type = highway_type[0]
        road_types[highway_type] = road_types.get(highway_type, 0) + 1

    return {
        "num_nodes": len(G.nodes),
        "num_edges": len(G.edges),
        "total_length_m": total_length,
        "road_types": road_types,
    }


def filter_residential_roads(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """
    Filter graph to keep only residential/local roads (exclude highways).
    """
    keep_types = {
        "residential",
        "living_street",
        "service",
        "unclassified",
        "tertiary",
        "secondary",
        "tertiary_link",
        "secondary_link",
    }

    G_filtered = G.copy()

    edges_to_remove = []
    for u, v, key, data in G_filtered.edges(keys=True, data=True):
        highway = data.get("highway", "unknown")
        if isinstance(highway, list):
            highway = highway[0]

        if highway not in keep_types and highway not in [
            "footway",
            "path",
            "pedestrian",
        ]:
            edges_to_remove.append((u, v, key))

    G_filtered.remove_edges_from(edges_to_remove)
    G_filtered.remove_nodes_from(list(nx.isolates(G_filtered)))

    logger.info(
        f"Filtered to {len(G_filtered.edges)} edges from {len(G.edges)} total"
    )

    return G_filtered
