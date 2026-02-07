"""
Route generation using a simplified Chinese Postman Problem approach.
"""
import networkx as nx
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def generate_route_for_zone(
    zone: nx.MultiDiGraph,
    start_point: Optional[Tuple[float, float]] = None,
    return_to_start: bool = False,
    travel_mode: str = "walking",
) -> Dict:
    """
    Generate an optimized delivery route through a zone.
    Uses a DFS-based traversal that attempts to cover all edges.

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
            "waypoints": [],
            "geometry": {"type": "LineString", "coordinates": []},
            "total_distance_m": 0,
            "turn_by_turn": [],
        }

    # Find start node
    if start_point:
        start_node = find_nearest_node(zone, start_point)
    else:
        lats = [data["y"] for _, data in zone.nodes(data=True)]
        lngs = [data["x"] for _, data in zone.nodes(data=True)]
        centroid = (sum(lats) / len(lats), sum(lngs) / len(lngs))
        start_node = find_nearest_node(zone, centroid)

    logger.info(f"Starting from node {start_node}")

    # Convert to undirected for walking
    if travel_mode == "walking":
        G_route = zone.to_undirected()
    else:
        G_route = zone.copy()

    route_nodes = generate_simple_route(G_route, start_node, return_to_start)

    # Convert to waypoints and compute distance
    waypoints = []
    total_distance = 0

    for i, node in enumerate(route_nodes):
        lat = zone.nodes[node]["y"]
        lng = zone.nodes[node]["x"]
        waypoints.append([lat, lng])

        if i > 0:
            prev_node = route_nodes[i - 1]
            edge_data = zone.get_edge_data(prev_node, node)
            if not edge_data:
                # Try reverse direction
                edge_data = zone.get_edge_data(node, prev_node)
            if edge_data:
                edge_key = list(edge_data.keys())[0]
                length = edge_data[edge_key].get("length", 0)
                total_distance += length

    turn_by_turn = generate_turn_by_turn(zone, route_nodes)

    geometry = {
        "type": "LineString",
        "coordinates": [[lng, lat] for lat, lng in waypoints],
    }

    return {
        "waypoints": waypoints,
        "geometry": geometry,
        "total_distance_m": total_distance,
        "turn_by_turn": turn_by_turn,
    }


def find_nearest_node(G: nx.Graph, point: Tuple[float, float]) -> int:
    """Find the nearest node to a given (lat, lng) point."""
    lat, lng = point
    min_dist = float("inf")
    nearest = None

    for node, data in G.nodes(data=True):
        node_lat = data["y"]
        node_lng = data["x"]
        dist = (node_lat - lat) ** 2 + (node_lng - lng) ** 2
        if dist < min_dist:
            min_dist = dist
            nearest = node

    return nearest


def generate_simple_route(
    G: nx.Graph, start_node: int, return_to_start: bool
) -> List[int]:
    """
    Generate a route that attempts to cover all edges using DFS with backtracking.
    """
    visited_edges = set()
    route = [start_node]
    current = start_node

    max_iterations = len(G.edges) * 3 + 100
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
            next_node = unvisited[0]
            route.append(next_node)
            edge = tuple(sorted([current, next_node]))
            visited_edges.add(edge)
            current = next_node
        else:
            # Find shortest path to a node with unvisited edges
            nodes_with_unvisited = set()
            for u, v in G.edges():
                edge = tuple(sorted([u, v]))
                if edge not in visited_edges:
                    nodes_with_unvisited.add(u)
                    nodes_with_unvisited.add(v)

            if not nodes_with_unvisited:
                break

            best_target = None
            best_path = None
            best_len = float("inf")

            for target in nodes_with_unvisited:
                try:
                    if nx.has_path(G, current, target):
                        path = nx.shortest_path(G, current, target, weight="length")
                        if len(path) < best_len:
                            best_len = len(path)
                            best_path = path
                            best_target = target
                except nx.NetworkXError:
                    continue

            if best_path:
                route.extend(best_path[1:])
                current = best_target
            else:
                break

    # Return to start if requested
    if return_to_start and current != start_node:
        try:
            if nx.has_path(G, current, start_node):
                return_path = nx.shortest_path(
                    G, current, start_node, weight="length"
                )
                route.extend(return_path[1:])
        except nx.NetworkXError:
            pass

    return route


def generate_turn_by_turn(G: nx.Graph, route_nodes: List[int]) -> List[Dict]:
    """Generate simplified turn-by-turn directions."""
    directions = []

    for i in range(len(route_nodes) - 1):
        current = route_nodes[i]
        next_node = route_nodes[i + 1]

        edge_data = G.get_edge_data(current, next_node)
        if not edge_data:
            edge_data = G.get_edge_data(next_node, current)
        if edge_data:
            edge_key = list(edge_data.keys())[0]
            street_name = edge_data[edge_key].get("name", "Unnamed Road")
            if isinstance(street_name, list):
                street_name = street_name[0]
            distance = edge_data[edge_key].get("length", 0)

            if i == 0:
                instruction = f"Start on {street_name}"
            else:
                instruction = f"Continue on {street_name}"

            directions.append(
                {
                    "instruction": instruction,
                    "distance_m": float(distance),
                    "street_name": street_name,
                }
            )

    # Merge consecutive same-street segments
    merged = []
    for direction in directions:
        if merged and merged[-1]["street_name"] == direction["street_name"]:
            merged[-1]["distance_m"] += direction["distance_m"]
        else:
            merged.append(direction.copy())

    for i, direction in enumerate(merged):
        direction["step"] = i + 1
        if i > 0:
            direction["instruction"] = f"Turn onto {direction['street_name']}"

    return merged


def calculate_route_duration(distance_m: float, travel_mode: str) -> float:
    """Estimate route duration in minutes."""
    if travel_mode == "walking":
        speed_kmh = 4.0
    else:
        speed_kmh = 30.0

    distance_km = distance_m / 1000
    duration_hours = distance_km / speed_kmh
    return duration_hours * 60
