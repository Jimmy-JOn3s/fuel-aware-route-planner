from django.contrib.gis.db import models


class Route(models.Model):
    start_point = models.PointField(geography=True)
    end_point = models.PointField(geography=True)
    geometry = models.LineStringField(geography=True, null=True, blank=True)
    fuel_stops = models.JSONField(default=list, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    route_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Route {self.id}"
