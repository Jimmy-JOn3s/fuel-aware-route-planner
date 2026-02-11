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


## Design choices and trade-offs
### Why Postgres + PostGIS over MongoDB
- Geospatial routing logic depends on SQL spatial operators (`ST_DWithin`, indexed distance filters) that PostGIS provides natively and efficiently.
- Station ingestion, deduplication, and route-history persistence fit relational constraints well (unique keys, transactions, typed decimals for fuel prices).
- Query planner + GiST/SP-GiST spatial indexes provide predictable performance for corridor filtering at scale.
- MongoDB geospatial features are useful, but this workload benefits more from relational joins, strict schema guarantees, and PostGIS geometry tooling.

### Why Redis
- Celery broker: reliable async task handoff for ingestion and background geocoding.
- Cache layer: low-latency lookup for repeated geocode and route requests, reducing external API calls and p95 response time.
- TTL-based cache expiry keeps data fresh while controlling memory growth.

### Architecture decisions
- Monolith-first service layout (web + worker) keeps delivery simple and maintainable while still demonstrating production patterns (async jobs, caching, geospatial DB).
- Fast ingest-first strategy loads CSV quickly; geocoding can run progressively in background to avoid blocking usability.
- On-demand routing uses one primary directions call and local optimization (Dijkstra) to stay within free-tier API limits.
- Route responses are persisted with timestamps for traceability, replay, and debugging.

## End-to-end flow
1. CSV ingestion loads fuel stations into Postgres.
2. Route request arrives with `start` and `end`.
3. API obtains route polyline from provider.
4. PostGIS filters stations within corridor distance of the route.
5. Graph is built with edge feasibility based on configured max leg distance.
6. Dijkstra finds the minimum fuel-cost path.
7. API returns route, fuel stops, gallons, and total cost.
8. Route response is cached in Redis for repeat lookups.

## Dijkstra fuel-optimization flow
- Candidate nodes are created from:
  - virtual `start` node,
  - virtual `end` node,
  - fuel stations near the route corridor (`ST_DWithin`).
- Directed edge `A -> B` is created only when:
  - `distance(A, B) <= VEHICLE_MAX_RANGE_MILES`.
- Edge fuel cost is computed as:
  - `gallons_for_leg = distance(A, B) / VEHICLE_MPG`
  - `leg_cost = gallons_for_leg * price_at_node_A`
- Dijkstra runs on this weighted graph to minimize total fuel cost from `start` to `end`.
- Total gallons are computed from full selected path distance:
  - `total_gallons = total_path_miles / VEHICLE_MPG`.
- For trips where direct start-to-end distance is within range, direct path is used and `fuel_stops` remains empty while cost is still returned.

### Parameter impact
- `VEHICLE_MAX_RANGE_MILES`
  - lower value: fewer reachable edges, more stops, possible no-path cases.
  - higher value: more reachable edges, fewer stops, often lower total cost.
- `VEHICLE_MPG`
  - higher value: lower gallons and lower total cost.
  - lower value: higher gallons and higher total cost.

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

## Provider endpoint configuration
- `MAPBOX_DIRECTIONS_BASE_URL` (default Mapbox driving directions endpoint)
- `ORS_DIRECTIONS_URL` (default ORS driving-car directions endpoint)
- `MAPBOX_GEOCODING_BASE_URL` (default Mapbox places geocoding endpoint)
- `ORS_GEOCODING_URL` (default ORS geocode search endpoint)
