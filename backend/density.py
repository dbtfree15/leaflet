"""
Building and address density estimation.
"""
import osmnx as ox
import networkx as nx
from shapely.geometry import Polygon, LineString
from typing import Dict, List
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
        buildings = ox.features_from_polygon(polygon, tags={"building": True})

        logger.info(f"Found {len(buildings)} buildings")

        building_list = []
        for idx, row in buildings.iterrows():
            building_type = row.get("building", "yes")
            levels = row.get("building:levels", 1)

            try:
                levels = int(float(levels))
            except (ValueError, TypeError):
                levels = 1

            building_list.append(
                {
                    "geometry": row["geometry"],
                    "type": building_type,
                    "levels": levels,
                    "centroid": row["geometry"].centroid,
                }
            )

        return building_list

    except Exception as e:
        logger.warning(f"Error fetching buildings: {e}")
        return []


def estimate_units_per_building(building: Dict) -> int:
    """Estimate number of dwelling units in a building."""
    building_type = building["type"]
    levels = building.get("levels", 1)

    if building_type in ["apartments", "residential", "house"]:
        if building_type == "apartments":
            return max(4 * levels, 4)
        else:
            return 1
    elif building_type in ["detached", "semidetached_house", "terrace"]:
        return 1
    else:
        return 1


def assign_buildings_to_edges(
    G: nx.MultiDiGraph, buildings: List[Dict], max_distance_m: float = 50
) -> nx.MultiDiGraph:
    """
    Assign buildings to nearest road edges and estimate addresses per edge.
    """
    logger.info("Assigning buildings to road edges...")

    for u, v, key in G.edges(keys=True):
        G[u][v][key]["estimated_addresses"] = 0

    if not buildings:
        logger.warning("No buildings found, using fallback estimation")
        return estimate_from_road_length(G)

    # Build edge geometries
    edge_lines = {}
    for u, v, key, data in G.edges(keys=True, data=True):
        if "geometry" in data:
            edge_lines[(u, v, key)] = data["geometry"]
        else:
            line = LineString(
                [
                    (G.nodes[u]["x"], G.nodes[u]["y"]),
                    (G.nodes[v]["x"], G.nodes[v]["y"]),
                ]
            )
            edge_lines[(u, v, key)] = line

    # Assign each building to nearest edge
    for building in buildings:
        centroid = building["centroid"]
        units = estimate_units_per_building(building)

        min_dist = float("inf")
        nearest_edge = None

        for edge, line in edge_lines.items():
            dist = centroid.distance(line)
            if dist < min_dist:
                min_dist = dist
                nearest_edge = edge

        # Convert threshold to approx degrees
        if nearest_edge and min_dist < max_distance_m / 111320:
            u, v, key = nearest_edge
            G[u][v][key]["estimated_addresses"] += units

    total_addresses = sum(
        data.get("estimated_addresses", 0) for _, _, data in G.edges(data=True)
    )
    logger.info(f"Total estimated addresses: {total_addresses}")

    return G


def estimate_from_road_length(
    G: nx.MultiDiGraph, density_multiplier: float = 20.0
) -> nx.MultiDiGraph:
    """Fallback: estimate addresses based on road length."""
    logger.info("Using road length fallback for density estimation")

    for u, v, key, data in G.edges(keys=True, data=True):
        length_m = data.get("length", 0)
        highway_type = data.get("highway", "residential")

        if isinstance(highway_type, list):
            highway_type = highway_type[0]

        density_map = {
            "residential": 20,
            "living_street": 30,
            "service": 5,
            "unclassified": 15,
            "tertiary": 10,
            "secondary": 5,
        }

        density = density_map.get(highway_type, 10)
        estimated = int((length_m / 100) * density)

        G[u][v][key]["estimated_addresses"] = max(estimated, 0)

    return G


def get_total_estimated_addresses(G: nx.MultiDiGraph) -> int:
    """Get total estimated addresses in the graph."""
    return sum(
        data.get("estimated_addresses", 0) for _, _, data in G.edges(data=True)
    )
