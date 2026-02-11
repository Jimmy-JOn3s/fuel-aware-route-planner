from decimal import Decimal

from django.contrib.gis.geos import Point

from routing.services import StationNode, build_graph, dijkstra, haversine_miles


def test_haversine_zero_distance():
    p = (0.0, 0.0)
    assert haversine_miles(p, p) == 0


def test_build_graph_respects_range():
    # Two nodes within 10 miles should connect; one far away should not.
    near_a = StationNode(id=1, lon=0, lat=0, price=Decimal("3.00"), name="A")
    near_b = StationNode(id=2, lon=0.1, lat=0, price=Decimal("3.50"), name="B")
    far = StationNode(id=3, lon=50, lat=50, price=Decimal("4.00"), name="Far")

    graph = build_graph([near_a, near_b, far])

    assert 2 in graph[1]  # edge exists
    assert 1 in graph[2]
    assert 3 not in graph[1]  # out of 500-mile range
    assert 3 not in graph[2]


def test_dijkstra_simple_path():
    # Graph: 1 -> 2 (cost 5), 1 -> 3 (cost 2), 3 -> 2 (cost 1) => shortest 1-3-2
    graph = {1: {2: 5, 3: 2}, 2: {}, 3: {2: 1}}
    path = dijkstra(graph, start=1, end=2)
    assert path == [1, 3, 2]
