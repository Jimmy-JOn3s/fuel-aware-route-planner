from decimal import Decimal

import pytest
from django.contrib.gis.geos import LineString
from rest_framework.test import APIClient

from routing.models import Route


@pytest.mark.django_db
def test_route_api_happy_path_persists_route(monkeypatch):
    def fake_compute_route(start_point, end_point):
        return {
            "route": {"features": [{"geometry": {"coordinates": [[0, 0], [1, 1]]}}]},
            "polyline": LineString((0, 0), (1, 1)),
            "fuel_stops": [{"name": "Demo Stop", "lon": 0.5, "lat": 0.5, "price": "3.111"}],
            "total_cost": Decimal("42.10"),
            "gallons": Decimal("12.30"),
        }

    monkeypatch.setattr("routing.views.compute_route", fake_compute_route)
    client = APIClient()
    response = client.post(
        "/api/route/",
        {"start": "-74.0060,40.7128", "end": "-77.0369,38.9072"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["total_cost"] == 42.1
    assert len(response.json()["fuel_stops"]) == 1
    assert Route.objects.count() == 1


@pytest.mark.django_db
def test_route_api_rejects_non_coordinate_input():
    client = APIClient()
    response = client.post(
        "/api/route/",
        {"start": "new york", "end": "-77.0369,38.9072"},
        format="json",
    )

    assert response.status_code == 400
    assert "Provide coordinates" in response.json()["detail"]


@pytest.mark.django_db
def test_route_api_validates_required_fields():
    client = APIClient()
    response = client.post("/api/route/", {"start": "-74.0060,40.7128"}, format="json")

    assert response.status_code == 400
    assert "end" in response.json()


@pytest.mark.django_db
def test_bdd_given_valid_coordinates_when_route_requested_then_returns_optimized_payload(monkeypatch):
    # Given: route computation is available and deterministic.
    def fake_compute_route(start_point, end_point):
        return {
            "route": {"features": [{"geometry": {"coordinates": [[0, 0], [1, 1]]}}]},
            "polyline": LineString((0, 0), (1, 1)),
            "fuel_stops": [],
            "total_cost": Decimal("15.75"),
            "gallons": Decimal("4.50"),
        }

    monkeypatch.setattr("routing.views.compute_route", fake_compute_route)
    client = APIClient()

    # When: client requests route with valid lon/lat pairs.
    response = client.post(
        "/api/route/",
        {"start": "-74.0060,40.7128", "end": "-77.0369,38.9072"},
        format="json",
    )

    # Then: API returns optimized route payload.
    body = response.json()
    assert response.status_code == 200
    assert "route" in body
    assert "fuel_stops" in body
    assert "gallons" in body
    assert "total_cost" in body


@pytest.mark.django_db
def test_bdd_given_unreachable_route_when_requested_then_returns_400(monkeypatch):
    monkeypatch.setattr(
        "routing.views.compute_route",
        lambda start_point, end_point: (_ for _ in ()).throw(
            ValueError("No feasible route found within VEHICLE_MAX_RANGE_MILES")
        ),
    )
    client = APIClient()

    response = client.post(
        "/api/route/",
        {"start": "-74.0060,40.7128", "end": "-118.2437,34.0522"},
        format="json",
    )

    assert response.status_code == 400
    assert "No feasible route found" in response.json()["detail"]
