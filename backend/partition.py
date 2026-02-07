"""
Zone partitioning algorithms for balanced route distribution.
"""
import networkx as nx
import numpy as np
from sklearn.cluster import KMeans
from typing import List, Dict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def partition_graph_into_zones(
    G: nx.MultiDiGraph, num_zones: int, balance_priority: str = "density"
) -> List[nx.MultiDiGraph]:
    """
    Partition graph into balanced zones using weighted k-means clustering.

    Args:
        G: Road network graph with 'estimated_addresses' on edges
        num_zones: Number of zones to create
        balance_priority: 'density' (balance by addresses) or 'area' (balance by distance)

    Returns:
        List of subgraphs, one per zone
    """
    logger.info(
        f"Partitioning graph into {num_zones} zones (priority: {balance_priority})"
    )

    if num_zones == 1:
        return [G.copy()]

    # Extract edge midpoints and weights
    edge_data = []
    for u, v, key, data in G.edges(keys=True, data=True):
        if "geometry" in data:
            midpoint = data["geometry"].interpolate(0.5, normalized=True)
            x, y = midpoint.x, midpoint.y
        else:
            x = (G.nodes[u]["x"] + G.nodes[v]["x"]) / 2
            y = (G.nodes[u]["y"] + G.nodes[v]["y"]) / 2

        if balance_priority == "density":
            weight = data.get("estimated_addresses", 0)
        else:
            weight = data.get("length", 0)

        edge_data.append(
            {"edge": (u, v, key), "x": x, "y": y, "weight": max(weight, 1)}
        )

    X = np.array([[e["x"], e["y"]] for e in edge_data])
    weights = np.array([e["weight"] for e in edge_data])

    # Weighted k-means: repeat points proportional to weight
    mean_weight = np.mean(weights)
    X_weighted = []
    edge_indices_weighted = []

    for i, (point, weight) in enumerate(zip(X, weights)):
        repeats = max(1, int(weight / mean_weight))
        X_weighted.extend([point] * repeats)
        edge_indices_weighted.extend([i] * repeats)

    X_weighted = np.array(X_weighted)

    kmeans = KMeans(n_clusters=num_zones, random_state=42, n_init=10)
    cluster_labels_weighted = kmeans.fit_predict(X_weighted)

    # Map back to original edges (majority vote)
    from collections import Counter

    edge_votes = defaultdict(list)
    for i, cluster in enumerate(cluster_labels_weighted):
        original_idx = edge_indices_weighted[i]
        edge_votes[original_idx].append(cluster)

    cluster_labels = np.zeros(len(edge_data), dtype=int)
    for idx, votes in edge_votes.items():
        cluster_labels[idx] = Counter(votes).most_common(1)[0][0]

    # Assign edges to zones
    zone_edges = defaultdict(list)
    for i, edge_info in enumerate(edge_data):
        zone_id = cluster_labels[i]
        zone_edges[zone_id].append(edge_info["edge"])

    # Create subgraphs for each zone
    zones = []
    for zone_id in range(num_zones):
        edges = zone_edges[zone_id]

        if not edges:
            logger.warning(f"Zone {zone_id} has no edges, skipping")
            continue

        subgraph = G.edge_subgraph(edges).copy()

        # Ensure connectivity - keep largest connected component
        if len(subgraph.edges) > 0:
            if not nx.is_weakly_connected(subgraph):
                components = list(nx.weakly_connected_components(subgraph))
                if components:
                    largest = max(components, key=len)
                    subgraph = subgraph.subgraph(largest).copy()

        subgraph.graph["zone_id"] = zone_id
        zones.append(subgraph)

    logger.info(f"Created {len(zones)} zones")
    for i, zone in enumerate(zones):
        total_weight = sum(
            data.get("estimated_addresses", 0)
            if balance_priority == "density"
            else data.get("length", 0)
            for _, _, data in zone.edges(data=True)
        )
        logger.info(f"  Zone {i}: {len(zone.edges)} edges, weight={total_weight:.0f}")

    return zones


def get_zone_stats(zone: nx.MultiDiGraph) -> Dict:
    """Get statistics for a zone."""
    total_addresses = sum(
        data.get("estimated_addresses", 0) for _, _, data in zone.edges(data=True)
    )
    total_length = sum(
        data.get("length", 0) for _, _, data in zone.edges(data=True)
    )

    lats = [data for _, data in zone.nodes(data="y")]
    lngs = [data for _, data in zone.nodes(data="x")]

    return {
        "num_edges": len(zone.edges),
        "num_nodes": len(zone.nodes),
        "estimated_addresses": int(total_addresses),
        "total_length_m": float(total_length),
        "bounds": {
            "min_lat": min(lats) if lats else 0,
            "max_lat": max(lats) if lats else 0,
            "min_lng": min(lngs) if lngs else 0,
            "max_lng": max(lngs) if lngs else 0,
        },
    }
