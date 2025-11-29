import networkx as nx
from pathlib import Path

from respiro.tools.sf_routing_engine import DatasetArtifacts, SFRoutingEngine, idw, pm25_to_aqi


def test_pm25_to_aqi_increases_with_pollution():
    assert pm25_to_aqi(10) < pm25_to_aqi(60)
    assert pm25_to_aqi(60) < pm25_to_aqi(200)


def test_idw_returns_exact_value_at_sensor():
    value = idw(37.7749, -122.4194, [(37.7749, -122.4194, 42.0)])
    assert value == 42.0


def test_engine_assigns_resp_cost(monkeypatch, tmp_path):
    graph = nx.MultiDiGraph()
    graph.add_node(1, x=-122.4, y=37.77)
    graph.add_node(2, x=-122.41, y=37.78)
    graph.add_edge(1, 2, key=0, length=100)

    artifacts = DatasetArtifacts(
        graph_path=tmp_path / "graph.graphml",
        pollution_baseline_path=tmp_path / "baseline.geojson",
        purpleair_snapshot_path=tmp_path / "sensors.json",
    )

    class DummyBuilder:
        def build(self, force_refresh=False):
            return artifacts

        def load_cached_graph(self):
            return graph

        def latest_purpleair_snapshot(self):
            return [{"latitude": 37.77, "longitude": -122.4, "pm25_corrected": 25}]

        def latest_aclima_baseline(self):
            return {}

    monkeypatch.setattr("respiro.tools.sf_routing_engine.SFDatasetBuilder", lambda: DummyBuilder())

    engine = SFRoutingEngine()
    u, v, data = next(engine.graph.edges(data=True))
    assert "respiratory_cost" in data
    assert engine.graph.nodes[u]["pollution_factor"] > 0

