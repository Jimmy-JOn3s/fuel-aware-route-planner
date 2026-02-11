from django.contrib.gis.geos import Point

import pytest

from routing.services import compute_route


def test_business_logic_short_trip_no_stops_but_non_zero_cost(monkeypatch):
    # Keep route under vehicle max range so no refuel stop is required.
    def fake_directions(self, start, end):
        return {
            "features": [
                {
                    "geometry": {
                        # ~69 miles
                        "coordinates": [[-74.0, 40.7], [-73.0, 40.7]]
                    }
                }
            ]
        }

    monkeypatch.setattr("routing.services.RoutingClient.directions", fake_directions)
    monkeypatch.setattr("routing.services.filter_stations_along_route", lambda polyline: [])

    payload = compute_route(Point(-74.0, 40.7), Point(-73.0, 40.7))

    assert payload["fuel_stops"] == []
    assert payload["gallons"] > 0
    assert payload["total_cost"] > 0


def test_business_logic_unreachable_when_max_range_too_low(monkeypatch):
    def fake_directions(self, start, end):
        return {
            "features": [
                {
                    "geometry": {
                        # ~1,500+ miles; no stations added, so impossible with tiny max range.
                        "coordinates": [[-74.0, 40.7], [-118.2, 34.0]]
                    }
                }
            ]
        }

    monkeypatch.setattr("routing.services.RoutingClient.directions", fake_directions)
    monkeypatch.setattr("routing.services.filter_stations_along_route", lambda polyline: [])
    monkeypatch.setattr("routing.services.MAX_RANGE_MILES", 50)

    with pytest.raises(ValueError, match="No feasible route found"):
        compute_route(Point(-74.0, 40.7), Point(-118.2, 34.0))
