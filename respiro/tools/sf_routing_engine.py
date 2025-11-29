"""
Clean-air routing engine for San Francisco.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from respiro.data import SFDatasetBuilder
from respiro.utils.logging import get_logger

logger = get_logger(__name__)


def _import_osmnx():
    try:
        import osmnx as ox  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("osmnx is required for routing. Run `pip install osmnx`.") from exc
    return ox


def pm25_to_aqi(pm25: float) -> float:
    """Approximate US AQI from PM2.5 concentration."""
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]
    for c_low, c_high, aqi_low, aqi_high in breakpoints:
        if c_low <= pm25 <= c_high:
            return ((aqi_high - aqi_low) / (c_high - c_low)) * (pm25 - c_low) + aqi_low
    return 500.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters."""
    r = 6371000  # Earth radius
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def idw(
    lat: float,
    lon: float,
    samples: List[Tuple[float, float, float]],
    k: int = 3,
    power: float = 2.0,
) -> float:
    """Simple inverse-distance weighting."""
    if not samples:
        return 0.0
    weighted = 0.0
    total_weight = 0.0
    sorted_samples = sorted(samples, key=lambda s: haversine_distance(lat, lon, s[0], s[1]))
    for sample_lat, sample_lon, value in sorted_samples[:k]:
        dist = haversine_distance(lat, lon, sample_lat, sample_lon)
        if dist == 0:
            return value
        weight = 1 / (dist**power)
        weighted += weight * value
        total_weight += weight
    return weighted / total_weight if total_weight else 0.0


@dataclass
class RouteResult:
    path: List[int]
    cost: float
    distance_meters: float
    duration_minutes: float
    geojson: Dict[str, Any]
    average_aqi: float


# Major parks in San Francisco (approximate centers for pollen penalty)
SF_PARKS = [
    (37.7694, -122.4862),  # Golden Gate Park
    (37.8024, -122.4058),  # Presidio
    (37.7946, -122.4093),  # Crissy Field
    (37.8014, -122.4476),  # Lands End
    (37.7879, -122.4095),  # Marina Green
    (37.7847, -122.4091),  # Fort Mason
]

PARK_RADIUS_METERS = 500  # 500m radius around parks for pollen penalty


class SFRoutingEngine:
    """Compute respiratory-aware routes for San Francisco."""

    def __init__(self) -> None:
        self.dataset = SFDatasetBuilder()
        artifacts = self.dataset.build(force_refresh=False)
        logger.info("Loaded dataset artifacts from %s", artifacts.graph_path.parent)
        self.graph = self.dataset.load_cached_graph()
        if self.graph is None:
            raise RuntimeError("San Francisco graph cache not found. Run SFDatasetBuilder.build().")
        self._prepare_graph()
        # Store dynamic context for route computation
        self.pollen_context: Dict[str, Any] = {}
        self.wind_context: Dict[str, Any] = {}

    def _prepare_graph(self) -> None:
        sensors = self.dataset.latest_purpleair_snapshot()
        sensor_points = []
        for sensor in sensors:
            try:
                lat = float(sensor.get("latitude"))
                lon = float(sensor.get("longitude"))
                pm25 = float(sensor.get("pm25_corrected") or sensor.get("pm2.5_alt") or 0.0)
            except (TypeError, ValueError):
                continue
            sensor_points.append((lat, lon, pm25))
        logger.info("Assigning pollution factors using %s PurpleAir sensors", len(sensor_points))
        for node_id, data in self.graph.nodes(data=True):
            lat = float(data.get("y"))
            lon = float(data.get("x"))
            pm25 = idw(lat, lon, sensor_points) if sensor_points else 12.0
            aqi = pm25_to_aqi(pm25)
            pollution_factor = min(aqi / 300.0, 1.5)
            data["pm25"] = pm25
            data["aqi"] = aqi
            data["pollution_factor"] = pollution_factor
            # Initialize pollen and wind factors (will be updated dynamically)
            data["pollen_penalty_factor"] = 0.0
            data["wind_adjustment_factor"] = 0.0

        for u, v, data in self.graph.edges(data=True):
            distance = float(data.get("length") or 1.0)
            grade = abs(float(data.get("grade_abs", data.get("grade", 0.0)) or 0.0))
            grade_penalty = 2.0 if grade > 0.05 else 0.0
            node_u = self.graph.nodes[u]
            node_v = self.graph.nodes[v]
            pollution_factor = (node_u.get("pollution_factor", 0.0) + node_v.get("pollution_factor", 0.0)) / 2
            # Base cost (will be adjusted dynamically for pollen/wind)
            data["respiratory_cost"] = distance * (1 + pollution_factor + grade_penalty)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    def compute_routes(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        pollen_context: Optional[Dict[str, Any]] = None,
        wind_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compute routes with optional pollen and wind context for dynamic adjustments.
        
        Args:
            start: Start coordinates (lat, lon)
            end: End coordinates (lat, lon)
            pollen_context: Dict with 'pollen_penalty' (bool) and 'pollen_alerts' (list)
            wind_context: Dict with 'direction_deg' (float) and 'speed_kmh' (float)
        """
        # Store context for dynamic adjustments
        self.pollen_context = pollen_context or {}
        self.wind_context = wind_context or {}
        
        # Apply dynamic cost adjustments
        self._apply_pollen_penalty()
        self._apply_wind_breaker()
        self._recompute_edge_costs()
        
        ox = _import_osmnx()
        start_node = ox.distance.nearest_nodes(self.graph, X=[start[1]], Y=[start[0]])[0]
        end_node = ox.distance.nearest_nodes(self.graph, X=[end[1]], Y=[end[0]])[0]

        fastest = self._shortest_path(start_node, end_node, weight="length")
        cleanest = self._shortest_path(start_node, end_node, weight="respiratory_cost")

        health_delta = (fastest.cost - cleanest.cost) / max(fastest.cost, 1.0)

        return {
            "fastest": fastest.geojson,
            "cleanest": cleanest.geojson,
            "health_delta": health_delta,
            "stats": {
                "fastest_minutes": fastest.duration_minutes,
                "cleanest_minutes": cleanest.duration_minutes,
                "fastest_aqi": fastest.average_aqi,
                "cleanest_aqi": cleanest.average_aqi,
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _shortest_path(self, start: int, end: int, weight: str) -> RouteResult:
        try:
            path = nx.shortest_path(self.graph, source=start, target=end, weight=weight)
        except nx.NetworkXNoPath as exc:
            raise RuntimeError(f"No {weight} path between nodes {start}->{end}") from exc
        distance = 0.0
        cost = 0.0
        for u, v in zip(path[:-1], path[1:]):
            edge_data = min(self.graph[u][v].values(), key=lambda d: float(d.get(weight, 0.0)))
            distance += float(edge_data.get("length", 0.0))
            cost += float(edge_data.get(weight, 0.0))
        avg_aqi = sum(self.graph[node].get("aqi", 0.0) for node in path) / len(path)
        geojson = self._path_to_geojson(path)
        duration_minutes = distance / 80.0  # assume 4.8 km/h walking speed
        return RouteResult(
            path=path,
            cost=cost,
            distance_meters=distance,
            duration_minutes=duration_minutes,
            geojson=geojson,
            average_aqi=avg_aqi,
        )

    def _path_to_geojson(self, path: List[int]) -> Dict[str, Any]:
        coordinates = [
            [float(self.graph.nodes[node]["x"]), float(self.graph.nodes[node]["y"])] for node in path
        ]
        return {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "LineString", "coordinates": coordinates},
        }
    
    def _apply_pollen_penalty(self) -> None:
        """
        Apply pollen penalty to nodes near parks when pollen is high.
        """
        pollen_penalty = self.pollen_context.get("pollen_penalty", False)
        if not pollen_penalty:
            # Reset pollen penalties
            for node_id, data in self.graph.nodes(data=True):
                data["pollen_penalty_factor"] = 0.0
            return
        
        logger.info("Applying pollen penalty to park-adjacent nodes")
        for node_id, data in self.graph.nodes(data=True):
            lat = float(data.get("y"))
            lon = float(data.get("x"))
            
            # Check distance to nearest park
            min_park_distance = min(
                haversine_distance(lat, lon, park_lat, park_lon)
                for park_lat, park_lon in SF_PARKS
            )
            
            # Apply penalty if within park radius
            if min_park_distance < PARK_RADIUS_METERS:
                # Penalty increases as you get closer to park center
                penalty_factor = 0.5 * (1 - min_park_distance / PARK_RADIUS_METERS)
                data["pollen_penalty_factor"] = penalty_factor
            else:
                data["pollen_penalty_factor"] = 0.0
    
    def _apply_wind_breaker(self) -> None:
        """
        Apply wind breaker cost adjustments based on wind direction.
        For westerly winds (200-340°): reduce cost of west-side edges
        For easterly winds (20-160°): reduce cost of east-side edges
        """
        wind_direction = self.wind_context.get("direction_deg")
        if wind_direction is None:
            # Reset wind adjustments
            for node_id, data in self.graph.nodes(data=True):
                data["wind_adjustment_factor"] = 0.0
            return
        
        logger.info("Applying wind breaker adjustments for wind direction %.1f°", wind_direction)
        
        # SF center longitude (roughly -122.4)
        SF_CENTER_LON = -122.4
        
        # Determine wind bias
        is_westerly = 200 <= wind_direction <= 340
        is_easterly = 20 <= wind_direction <= 160
        
        if not (is_westerly or is_easterly):
            # Neutral wind, no adjustment
            for node_id, data in self.graph.nodes(data=True):
                data["wind_adjustment_factor"] = 0.0
            return
        
        # Apply cost reduction based on location relative to wind
        for node_id, data in self.graph.nodes(data=True):
            lon = float(data.get("x"))
            
            if is_westerly:
                # Westerly wind: reduce cost for west-side nodes (lon < center)
                if lon < SF_CENTER_LON:
                    # Reduce cost by 25% for west-side nodes
                    data["wind_adjustment_factor"] = -0.25
                else:
                    data["wind_adjustment_factor"] = 0.0
            elif is_easterly:
                # Easterly wind: reduce cost for east-side nodes (lon > center)
                if lon > SF_CENTER_LON:
                    # Reduce cost by 25% for east-side nodes
                    data["wind_adjustment_factor"] = -0.25
                else:
                    data["wind_adjustment_factor"] = 0.0
    
    def _recompute_edge_costs(self) -> None:
        """
        Recompute edge costs with dynamic adjustments (pollen, wind).
        """
        for u, v, data in self.graph.edges(data=True):
            distance = float(data.get("length") or 1.0)
            grade = abs(float(data.get("grade_abs", data.get("grade", 0.0)) or 0.0))
            grade_penalty = 2.0 if grade > 0.05 else 0.0
            
            node_u = self.graph.nodes[u]
            node_v = self.graph.nodes[v]
            
            # Average pollution factor
            pollution_factor = (node_u.get("pollution_factor", 0.0) + node_v.get("pollution_factor", 0.0)) / 2
            
            # Average pollen penalty
            pollen_penalty = (node_u.get("pollen_penalty_factor", 0.0) + node_v.get("pollen_penalty_factor", 0.0)) / 2
            
            # Average wind adjustment
            wind_adjustment = (node_u.get("wind_adjustment_factor", 0.0) + node_v.get("wind_adjustment_factor", 0.0)) / 2
            
            # Apply wind adjustment as multiplier (negative adjustment = cost reduction)
            base_cost = distance * (1 + pollution_factor + grade_penalty + pollen_penalty)
            data["respiratory_cost"] = base_cost * (1 + wind_adjustment)

