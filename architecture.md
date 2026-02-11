# Pathfinder Architecture Overview

## High-level service/data-traffic diagram
```mermaid
flowchart LR
    C["Client (Postman / Frontend)"] -->|HTTP| W["Django API (web)"]
    W -->|enqueue ingest/geocode jobs| R["Redis (broker + cache)"]
    R -->|Celery tasks| K["Celery Worker"]

    W -->|read/write stations + routes| P["Postgres + PostGIS"]
    K -->|bulk ingest + geocode updates| P

    W -->|on-demand route + geocode calls| M["Mapbox APIs"]
    K -->|nightly/backfill geocode calls| O["OpenRouteService APIs"]

    W <-->|route/geocode cache| R
    C <-->|JSON response (route, fuel stops, cost)| W
```

## High-level flow
1) **Ingest CSV (fast, no external calls):** Load all stations into PostGIS; leave `geom` null initially.  
2) **On-demand routing (user request):**
   - Geocode start/end (fast provider).
   - Geocode only corridor stations missing coords (cached).
   - Filter stations near the route, build graph, run Dijkstra, respond.
   - Cache the final route response by `start|end`.
3) **Background trickle geocoding (nightly):** Fill `geom` for remaining stations within daily quota.

## Geocoding & routing providers
- **On-demand provider (fast path):** **Mapbox** geocoding/routing (you’ll supply `MAPBOX_API_KEY`). It’s generally faster and has a generous free tier (100k geocodes/month) for interactive requests.
- **Batch provider (nightly):** **OpenRouteService (ORS)** geocoding with the 20k/day cap. Use it to slowly backfill missing station coords without blocking users.
- **Fallback (US-only, if needed):** Census Geocoder for addresses that fail or to reduce paid quota.

## Caching strategy
- **Geocode cache (Redis):** key `geocode:{normalized_address}` → `{lon, lat, provider, ts}`. Always check cache before calling any provider; write-through on success.
- **Route cache (Redis):** key `route:{start}|{end}` → full API response. Short TTL for freshness; avoids repeat ORS/Mapbox hits.
- **DB state:** Once a station is geocoded, persist `geom` so future requests never re-geocode it.

## Ingest modes
- **Fast load (default):** Import CSV, skip geocoding if no API key is present; everything lands with `geom=null`.
- **Optional geocode during ingest:** If `MAPBOX_API_KEY` is set, geocode during ingest but cap requests (e.g., 5–10 qps) and use the Redis cache.

## Background job (nightly)
- Celery task `geocode_pending`:
  - Select stations with `geom IS NULL`.
  - Respect a daily cap (e.g., 20k) and back off on rate limits.
  - Use cache; attempt Mapbox first, ORS second; write `geom` on success.

## Routing pipeline (on-demand)
1) Validate/parse start & end; geocode if they’re not coordinates.
2) Fetch route polyline (Mapbox or ORS directions) with up to 2 retries.
3) Select nearby stations via PostGIS `ST_DWithin` on the polyline.
4) Geocode any selected stations lacking `geom` (cache first, Mapbox first).
5) Build reachability graph (500-mile constraint); edge weight = fuel cost.
6) Run Dijkstra; return stops, cost, gallons, static map URL.
7) Cache route response.

## Environment keys
- `MAPBOX_API_KEY` — used for on-demand geocoding/routing.
- `ORS_API_KEY` — used for nightly batch geocoding and as routing fallback.
- `REDIS_URL`, `DATABASE_URL` — existing.

## Next implementation steps
1) Wire geocode cache (Redis) and dual-provider geocode helper (Mapbox → ORS → fallback).
2) Make ingest skip geocode when no key; optional capped geocode when key present.
3) Add `geocode_pending` Celery task with daily cap.
4) Add route-response cache and static map URL generation (Mapbox).
5) Add admin/management command to monitor geocode backlog counts.
