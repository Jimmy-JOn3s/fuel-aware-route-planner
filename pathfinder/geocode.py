from __future__ import annotations

import json
import time
from typing import Optional, Tuple

import requests
import redis
from django.conf import settings

_redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
_http = requests.Session()


def _cache_key(address: str) -> str:
    return f"geocode:{address.strip().lower()}"


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Geocode an address using Mapbox first, then ORS.
    Returns (lon, lat) or None. Caches successful hits in Redis.
    """
    key = _cache_key(address)
    cached = _redis.get(key)
    if cached:
        try:
            lon, lat = json.loads(cached)
            return float(lon), float(lat)
        except (ValueError, TypeError):
            pass

    # Mapbox primary
    if settings.MAPBOX_API_KEY:
        coords = _geocode_mapbox(address)
        if coords:
            _redis.set(key, json.dumps(coords), ex=60 * 60 * 24 * 30)
            return coords

    # ORS fallback
    if settings.ORS_API_KEY:
        coords = _geocode_ors(address)
        if coords:
            _redis.set(key, json.dumps(coords), ex=60 * 60 * 24 * 30)
            return coords

    return None


def _geocode_mapbox(address: str) -> Optional[Tuple[float, float]]:
    url = f"{settings.MAPBOX_GEOCODING_BASE_URL.rstrip('/')}/{address}.json"
    params = {"access_token": settings.MAPBOX_API_KEY, "limit": 1, "autocomplete": "false"}
    for _ in range(max(1, settings.MAPBOX_GEOCODE_MAX_ATTEMPTS)):
        try:
            resp = _http.get(url, params=params, timeout=settings.HTTP_TIMEOUT_SECONDS)
            if not resp.ok:
                continue
            data = resp.json()
            feat = data.get("features", [])
            if not feat:
                return None
            lon, lat = feat[0]["center"]
            return float(lon), float(lat)
        except Exception:
            continue
    return None


def _geocode_ors(address: str) -> Optional[Tuple[float, float]]:
    url = settings.ORS_GEOCODING_URL
    params = {"api_key": settings.ORS_API_KEY, "text": address, "size": 1}
    for _ in range(max(1, settings.ORS_GEOCODE_MAX_ATTEMPTS)):
        try:
            resp = _http.get(url, params=params, timeout=settings.HTTP_TIMEOUT_SECONDS)
            if not resp.ok:
                continue
            data = resp.json()
            feat = data["features"][0]
            lon, lat = feat["geometry"]["coordinates"]
            return float(lon), float(lat)
        except Exception:
            continue
    return None
