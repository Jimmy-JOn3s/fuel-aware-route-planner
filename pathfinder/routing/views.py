from decimal import Decimal
from typing import Any

from django.contrib.gis.geos import Point
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RouteRequestSerializer
from .services import compute_route
from .models import Route
import logging
import time

logger = logging.getLogger(__name__)


class RouteView(APIView):
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Response:
        t0 = time.perf_counter()
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start_raw = serializer.validated_data["start"]
        end_raw = serializer.validated_data["end"]

        def parse_point(raw: str) -> Point:
            if "," in raw:
                lon, lat = raw.split(",", 1)
                return Point(float(lon), float(lat))
            raise ValueError("Lat/Lon required when not using geocoding")

        try:
            start_point = parse_point(start_raw)
            end_point = parse_point(end_raw)
        except ValueError:
            return Response(
                {"detail": "Provide coordinates as 'lon,lat' strings"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = compute_route(start_point, end_point)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        payload["static_map_url"] = ""

        Route.objects.create(
            start_point=start_point,
            end_point=end_point,
            geometry=payload.get("polyline"),
            fuel_stops=payload.get("fuel_stops", []),
            total_cost=payload.get("total_cost"),
            route_json=payload.get("route", {}),
        )

        payload.pop("polyline", None)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info("Route request %s -> %s completed in %.1f ms", start_raw, end_raw, elapsed)
        return Response(payload)
