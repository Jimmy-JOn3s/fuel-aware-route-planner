# Pathfinder Fuel Optimization Route

API service for cost-aware routing and fuel-stop optimization in the USA.

## What the system does
- Accepts start and end locations.
- Fetches a drivable route from a map provider.
- Selects stations near the route corridor.
- Applies a configurable vehicle range constraint.
- Computes fuel stops and total fuel cost with configurable MPG.
- Returns route geometry, stop list, gallons, and total cost.

## High-level architecture
- **Django API (web):** request validation, routing orchestration, response shaping.
- **Postgres + PostGIS:** persistent station data, geospatial queries, route history.
- **Redis:** Celery broker and cache for geocode/route responses.
- **Celery worker:** asynchronous ingestion and background geocoding tasks.
- **Mapbox:** on-demand geocoding and routing for interactive speed.
- **OpenRouteService (ORS):** batch geocoding/backfill path.

Reference diagram: `architecture.md`

## End-to-end flow
1. CSV ingestion loads fuel stations into Postgres.
2. Route request arrives with `start` and `end`.
3. API obtains route polyline from provider.
4. PostGIS filters stations within corridor distance of the route.
5. Graph is built with edge feasibility based on configured max leg distance.
6. Dijkstra finds the minimum fuel-cost path.
7. API returns route, fuel stops, gallons, and total cost.
8. Route response is cached in Redis for repeat lookups.

## Background jobs and freshness model
- Background geocoding tasks continuously fill missing station coordinates (`geom`).
- Backfill runs in batches to respect API quotas and avoid request spikes.
- Cache keys include location/request signatures and TTL controls to prevent stale growth.
- Route history is stored with timestamps for audit and replay.
- If provider roads, traffic models, or geometry change, fresh requests re-query routing APIs and refresh cached responses.
- If route coverage expands into new areas, nightly/backfill jobs geocode newly relevant stations so stop selection remains accurate.

## Why background jobs exist
- Interactive API latency stays low by moving heavy enrichment outside request time.
- Large CSV datasets become usable quickly even before full geocode completion.
- Progressive enrichment improves stop quality over time without blocking route responses.
- Scheduled refresh keeps station coverage aligned with evolving route patterns.

## Core constraints implemented
- Vehicle max range: `VEHICLE_MAX_RANGE_MILES` (default `500`).
- Fuel economy: `VEHICLE_MPG` (default `10`).
- Fuel prices sourced from uploaded CSV dataset.
- External routing API usage minimized and cached.
