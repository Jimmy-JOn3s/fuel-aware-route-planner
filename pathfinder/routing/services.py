from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple

import requests
from django.conf import settings
from django.contrib.gis.geos import LineString, Point
from ingest.models import FuelStation
from pathfinder.geocode import geocode_address

MILES_PER_GALLON = Decimal(str(settings.VEHICLE_MPG))
MAX_RANGE_MILES = float(settings.VEHICLE_MAX_RANGE_MILES)


@dataclass
class StationNode:
    id: int
    lon: float
    lat: float
    price: Decimal
    name: str


class RoutingClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.MAPBOX_API_KEY or settings.ORS_API_KEY

    def directions(self, start: Tuple[float, float], end: Tuple[float, float]) -> dict:
        if settings.MAPBOX_API_KEY:
            return self._directions_mapbox(start, end)
        if settings.ORS_API_KEY:
            return self._directions_ors(start, end)
        raise ValueError("No routing API key configured")

    def _directions_mapbox(self, start: Tuple[float, float], end: Tuple[float, float]) -> dict:
        url = (
            f"https://api.mapbox.com/directions/v5/mapbox/driving/"
            f"{start[0]},{start[1]};{end[0]},{end[1]}"
        )
        params = {"access_token": settings.MAPBOX_API_KEY, "geometries": "geojson"}
        for attempt in range(3):
            resp = requests.get(url, params=params, timeout=10)
            if resp.ok:
                data = resp.json()
                # Normalize to ORS-like shape
                coords = data["routes"][0]["geometry"]["coordinates"]
                return {"features": [{"geometry": {"coordinates": coords}}]}
        resp.raise_for_status()

    def _directions_ors(self, start: Tuple[float, float], end: Tuple[float, float]) -> dict:
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        params = {
            "api_key": settings.ORS_API_KEY,
            "start": f"{start[0]},{start[1]}",
            "end": f"{end[0]},{end[1]}",
        }
        for attempt in range(3):
            resp = requests.get(url, params=params, timeout=10)
            if resp.ok:
                return resp.json()
        resp.raise_for_status()


def haversine_miles(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    lon1, lat1 = p1
    lon2, lat2 = p2
    R = 3958.8
    dlon = math.radians(lon2 - lon1)
    dlat = math.radians(lat2 - lat1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(
        math.radians(lat2)
    ) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def filter_stations_along_route(polyline: LineString, corridor_miles: float = 25) -> List[StationNode]:
    # Quick spatial filter using PostGIS via queryset
    corridor_meters = corridor_miles * 1609.34
    qs = (
        FuelStation.objects.annotate()
        .filter(geom__distance_lte=(polyline, corridor_meters))
        .only("id", "geom", "price", "name")
    )
    nodes: List[StationNode] = []
    for station in qs:
        if station.geom:
            nodes.append(
                StationNode(
                    id=station.id,
                    lon=station.geom.x,
                    lat=station.geom.y,
                    price=station.price,
                    name=station.name,
                )
            )
    return nodes


def build_graph(nodes: List[StationNode]) -> Dict[int, Dict[int, float]]:
    graph: Dict[int, Dict[int, float]] = {node.id: {} for node in nodes}
    coords = {node.id: (node.lon, node.lat) for node in nodes}
    prices = {node.id: node.price for node in nodes}
    for a in nodes:
        for b in nodes:
            if a.id == b.id:
                continue
            dist = haversine_miles(coords[a.id], coords[b.id])
            if dist <= MAX_RANGE_MILES:
                gallons = Decimal(dist) / MILES_PER_GALLON
                # Fuel cost is paid at the source stop before driving the leg.
                cost = gallons * prices[a.id]
                graph[a.id][b.id] = float(cost)
    return graph


def dijkstra(graph: Dict[int, Dict[int, float]], start: int, end: int) -> List[int]:
    import heapq

    queue: List[Tuple[float, int]] = [(0.0, start)]
    dist: Dict[int, float] = {start: 0.0}
    prev: Dict[int, int] = {}

    while queue:
        cost, node = heapq.heappop(queue)
        if node == end:
            break
        for neighbor, weight in graph.get(node, {}).items():
            new_cost = cost + weight
            if new_cost < dist.get(neighbor, float("inf")):
                dist[neighbor] = new_cost
                prev[neighbor] = node
                heapq.heappush(queue, (new_cost, neighbor))

    path: List[int] = []
    node = end
    while node in prev or node == start:
        path.append(node)
        if node == start:
            break
        node = prev[node]
    path.reverse()
    return path


def compute_route(start_point: Point, end_point: Point) -> dict:
    client = RoutingClient()
    directions = client.directions((start_point.x, start_point.y), (end_point.x, end_point.y))
    coords = directions["features"][0]["geometry"]["coordinates"]
    polyline = LineString(coords)

    # Build node list including virtual start/end nodes.
    stations = filter_stations_along_route(polyline)
    # Use nearest station price as a baseline for virtual nodes so short routes still
    # produce realistic non-zero fuel cost even when no stop is needed.
    if stations:
        nearest_start = min(
            stations,
            key=lambda n: haversine_miles((start_point.x, start_point.y), (n.lon, n.lat)),
        )
        baseline_price = nearest_start.price
    else:
        baseline_price = Decimal("3.500")

    start_node = StationNode(
        id=-1, lon=start_point.x, lat=start_point.y, price=baseline_price, name="start"
    )
    end_node = StationNode(
        id=-2, lon=end_point.x, lat=end_point.y, price=baseline_price, name="end"
    )
    nodes = [start_node, end_node] + stations

    direct_distance = haversine_miles((start_point.x, start_point.y), (end_point.x, end_point.y))

    graph = build_graph(nodes)
    path_ids = dijkstra(graph, start_node.id, end_node.id)
    if not path_ids:
        path_ids = [start_node.id, end_node.id]
    # For trips that fit in one tank, avoid synthetic intermediate stops.
    if direct_distance <= MAX_RANGE_MILES:
        path_ids = [start_node.id, end_node.id]
    nodes_by_id = {n.id: n for n in nodes}
    ordered = [nodes_by_id[node_id] for node_id in path_ids if node_id not in (-1, -2)]

    # Compute totals
    total_cost = sum(graph[path_ids[i]][path_ids[i + 1]] for i in range(len(path_ids) - 1))
    total_distance = sum(
        haversine_miles(
            (nodes_by_id[path_ids[i]].lon, nodes_by_id[path_ids[i]].lat),
            (nodes_by_id[path_ids[i + 1]].lon, nodes_by_id[path_ids[i + 1]].lat),
        )
        for i in range(len(path_ids) - 1)
    )
    gallons = Decimal(total_distance) / MILES_PER_GALLON

    return {
        "route": directions,
        "polyline": polyline,
        "fuel_stops": [
            {
                "name": node.name,
                "lon": node.lon,
                "lat": node.lat,
                "price": str(node.price),
            }
            for node in ordered
        ],
        "total_cost": round(Decimal(total_cost), 2),
        "gallons": round(gallons, 2),
    }
