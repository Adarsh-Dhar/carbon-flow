"""
San Francisco Golden Dataset builder.

This module centralizes the logic for downloading and caching the OSM graph,
attaching elevation + grade metadata, and persisting auxiliary pollution layers
that power the clean-air routing engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import networkx as nx

from respiro.config.settings import get_settings
from respiro.integrations.aclima import AclimaClient
from respiro.integrations.purpleair import PurpleAirClient
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

SF_BOUNDING_BOX = ((37.70, -122.52), (37.81, -122.35))
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "sf_routing"
GRAPHML_FILENAME = "sf_base.graphml"
POLLUTION_BASELINE_FILENAME = "aclima_baseline.geojson"
PURPLEAIR_SNAPSHOT_FILENAME = "purpleair_snapshot.json"


def _import_osmnx() -> Any:
    try:
        import osmnx as ox  # type: ignore
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "osmnx is required for San Francisco routing. "
            "Run `pip install osmnx geopandas rasterio`."
        ) from exc
    return ox


@dataclass
class DatasetArtifacts:
    graph_path: Path
    pollution_baseline_path: Path
    purpleair_snapshot_path: Path


class SFDatasetBuilder:
    """Create or refresh the San Francisco routing dataset."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        network_type: str = "bike",
    ) -> None:
        self.settings = get_settings()
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.network_type = network_type
        self.purpleair = PurpleAirClient()
        self.aclima = AclimaClient()
        logger.debug("Initialized SFDatasetBuilder cache=%s", self.cache_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build(self, force_refresh: bool = False) -> DatasetArtifacts:
        """
        Build the dataset, optionally forcing a refresh from source APIs.

        Returns paths to cached artifacts ready for the routing engine.
        """
        graph_path = self.cache_dir / GRAPHML_FILENAME
        if force_refresh or not graph_path.exists():
            logger.info("Caching base OSM graph for San Francisco (force=%s)", force_refresh)
            graph = self._download_graph()
            graph = self._attach_elevation_and_grades(graph)
            graph = self._sanitize_for_graphml(graph)
            nx.write_graphml(graph, graph_path)
            logger.info("Saved graph with %s nodes / %s edges", graph.number_of_nodes(), graph.number_of_edges())

        pollution_baseline_path = self.cache_dir / POLLUTION_BASELINE_FILENAME
        if force_refresh or not pollution_baseline_path.exists():
            baseline = self.aclima.fetch_airview_geojson(SF_BOUNDING_BOX)
            pollution_baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            logger.info("Cached Aclima baseline containing %s features", len(baseline.get("features", [])))

        purpleair_snapshot_path = self.cache_dir / PURPLEAIR_SNAPSHOT_FILENAME
        if force_refresh or not purpleair_snapshot_path.exists():
            sensors = self.purpleair.fetch_sf_sensors()
            purpleair_snapshot_path.write_text(json.dumps(sensors), encoding="utf-8")
            logger.info("Cached PurpleAir snapshot with %s sensors", len(sensors))

        return DatasetArtifacts(
            graph_path=graph_path,
            pollution_baseline_path=pollution_baseline_path,
            purpleair_snapshot_path=purpleair_snapshot_path,
        )

    def refresh_realtime_layers(self) -> Path:
        """
        Refresh only the dynamic PurpleAir snapshot.
        """
        sensors = self.purpleair.fetch_sf_sensors()
        snapshot_path = self.cache_dir / PURPLEAIR_SNAPSHOT_FILENAME
        snapshot_path.write_text(json.dumps(sensors), encoding="utf-8")
        logger.info("Refreshed PurpleAir snapshot with %s sensors", len(sensors))
        return snapshot_path

    # ------------------------------------------------------------------
    # Graph helpers
    # ------------------------------------------------------------------
    def _download_graph(self) -> nx.MultiDiGraph:
        ox = _import_osmnx()
        logger.info("Downloading OSM graph for San Francisco network=%s", self.network_type)
        graph = ox.graph_from_place("San Francisco, California", network_type=self.network_type)
        return graph

    def _sanitize_for_graphml(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        """
        Clean up node/edge attributes so NetworkX's GraphML writer can serialize them.

        - Drop known problematic geometry keys entirely.
        - Coerce any remaining non-primitive values (lists, dicts, shapely objects, etc.)
          to strings so they become valid GraphML attribute values.
        """
        bad_keys = {"geometry", "geom", "shapely_geometry"}
        primitive_types = (str, int, float, bool)

        def _sanitize_attr_dict(attr: Dict[str, Any]) -> None:
            for key in list(attr.keys()):
                if key in bad_keys:
                    del attr[key]
                    continue

                value = attr[key]
                if value is None:
                    continue

                # If the value is not a primitive, coerce it to string
                if not isinstance(value, primitive_types):
                    try:
                        attr[key] = str(value)
                    except Exception:
                        # As a last resort, drop the attribute
                        del attr[key]

        # Sanitize nodes
        for _, data in graph.nodes(data=True):
            _sanitize_attr_dict(data)

        # Sanitize edges
        for _, _, _, data in graph.edges(keys=True, data=True):
            _sanitize_attr_dict(data)

        return graph

    def _attach_elevation_and_grades(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        """
        Attach elevation and grade metadata to the graph.

        This step is best-effort: if external elevation services or osmnx helpers
        fail, we log and fall back to the base graph rather than crashing the
        routing engine.
        """
        ox = _import_osmnx()
        api_key = self.settings.api.google_maps_api_key

        try:
            if api_key:
                logger.info("Adding elevation data via Google Elevation API")
                try:
                    graph = ox.add_node_elevations_google(graph, api_key=api_key)
                except Exception as exc:
                    logger.error("Google elevation failed: %s", exc)
            else:
                # No Google key available; skip elevation enrichment entirely
                logger.warning("Google Maps API key missing; skipping elevation enrichment")

            logger.info("Computing edge grades (slopes)")
            try:
                graph = ox.add_edge_grades(graph)
            except Exception as exc:
                logger.error("Edge grade computation failed, using base graph: %s", exc)

            return graph
        except Exception as exc:  # pragma: no cover - defensive guardrail
            logger.error("Elevation/grade enrichment failed, using base graph: %s", exc)
            return graph

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    def load_cached_graph(self) -> Optional[nx.MultiDiGraph]:
        graph_path = self.cache_dir / GRAPHML_FILENAME
        if not graph_path.exists():
            logger.warning("Cached graph not found at %s", graph_path)
            return None
        logger.info("Loading cached graph from %s", graph_path)
        try:
            return nx.read_graphml(graph_path)
        except Exception as exc:
            # If the cached GraphML is corrupt/empty, rebuild once with force_refresh
            logger.error("Failed to read cached graph (%s); rebuilding dataset: %s", graph_path, exc)
            artifacts = self.build(force_refresh=True)
            logger.info("Rebuilt SF dataset artifacts at %s", artifacts.graph_path)
            try:
                return nx.read_graphml(artifacts.graph_path)
            except Exception as exc2:
                logger.error("Failed to read rebuilt graphml at %s: %s", artifacts.graph_path, exc2)
                return None

    def latest_purpleair_snapshot(self) -> List[Dict[str, Any]]:
        snapshot_path = self.cache_dir / PURPLEAIR_SNAPSHOT_FILENAME
        if not snapshot_path.exists():
            return []
        return json.loads(snapshot_path.read_text(encoding="utf-8"))

    def latest_aclima_baseline(self) -> Dict[str, Any]:
        baseline_path = self.cache_dir / POLLUTION_BASELINE_FILENAME
        if not baseline_path.exists():
            return {"type": "FeatureCollection", "features": []}
        return json.loads(baseline_path.read_text(encoding="utf-8"))


def build_sf_dataset(force_refresh: bool = False) -> DatasetArtifacts:
    """
    Convenience wrapper used by scripts/CLIs.
    """
    builder = SFDatasetBuilder()
    return builder.build(force_refresh=force_refresh)

