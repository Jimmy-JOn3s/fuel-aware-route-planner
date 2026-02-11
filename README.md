# Pathfinder Fuel Optimization Route

Cost-aware routing API for US trips.  
Returns route geometry, fuel stops, gallons, and total fuel cost.

## TL;DR
- Stack: Django + DRF, Postgres/PostGIS, Redis, Celery, Mapbox (primary), ORS (fallback/batch).
- Routing optimization: Dijkstra on a fuel-cost graph with max-range constraints.
- Ingest supports daily CSV refresh via async upload route.
- Geocoding supports fast-load (`geom=NULL`) + progressive background backfill.
- Cold route latency improved from ~4.0s to ~900ms after HTTP/provider tuning.

## API docs
- Swagger UI: `http://localhost:8000/api/docs/`
- OpenAPI schema: `http://localhost:8000/api/schema/`

## Local setup
1. `cp .env.example .env`
2. Set keys in `.env`:
   - `MAPBOX_API_KEY=...`
   - `ORS_API_KEY=...` (optional)
3. Start services: `docker compose up --build -d`
4. Upload dataset: `POST /api/ingest/upload/` with multipart field `file`
5. If `INGEST_GEOCODE=False`, run one progressive backfill loop (batch + sleep):
   - `docker compose exec web python /app/pathfinder/manage.py shell -c "import time; from ingest.tasks import geocode_pending; total=0; batch=500; sleep_s=1; print(f'start batch={batch} sleep={sleep_s}s');\nwhile True:\n    n=geocode_pending(batch_size=batch)\n    total+=n\n    print(f'updated={n} total={total}')\n    if n==0:\n        break\n    time.sleep(sleep_s)\nprint('done')"`
   - recommended starter values for basic-tier safety (`batch=400`, `sleep_s=2`):  
     `docker compose exec web python /app/pathfinder/manage.py shell -c "import time; from ingest.tasks import geocode_pending; total=0; batch=400; sleep_s=2; print(f'start batch={batch} sleep={sleep_s}s');\nwhile True:\n    n=geocode_pending(batch_size=batch)\n    total+=n\n    print(f'updated={n} total={total}')\n    if n==0:\n        break\n    time.sleep(sleep_s)\nprint('done')"`
6. Check geocode progress:
   - `docker compose exec db psql -U pathfinder -d pathfinder -c "SELECT COUNT(*) AS total, COUNT(geom) AS geocoded, COUNT(*)-COUNT(geom) AS remaining_null FROM ingest_fuelstation;"`

## Core routes
- `POST /api/ingest/upload/` - async CSV ingestion
- `GET /api/ingest/status/{id}/` - ingestion status
- `POST /api/route/` - route + fuel optimization

## Tests (unit, API, BDD, business rules)

### Run test suite
- `docker compose exec web pytest -q`

### Current coverage by file
- `tests/test_routing.py` (unit tests)
  - `haversine_miles` zero-distance behavior
  - graph range constraints in `build_graph`
  - shortest-path selection in `dijkstra`

- `tests/test_ingest_tasks.py` (unit + task behavior)
  - price parsing/quantization (`parse_price`)
  - ingest happy path updates station + marks ingestion success
  - ingest failure path marks ingestion failed with error detail

- `tests/test_ingest_api.py` (API + BDD style)
  - missing file returns `400`
  - upload queues Celery task and creates ingestion record
  - status endpoint returns expected ingestion payload
  - BDD scenario: given missing file, when upload called, then `400`

- `tests/test_routing_api.py` (API + BDD style)
  - happy path returns route payload and persists route record
  - validation failures for bad coordinates / missing fields
  - BDD scenario: given valid coordinates, when route requested, then optimized payload
  - BDD scenario: given unreachable route, when requested, then `400` with feasibility message

- `tests/test_routing_business_logic.py` (business-logic focus)
  - short trip under max range: no stops but non-zero gallons/cost
  - unreachable trip under strict range: raises `ValueError` for infeasible route

## Architecture overview
- **Web API**: request validation, routing orchestration, persistence.
- **Postgres + PostGIS**: stations, geospatial filtering (`ST_DWithin`), route history.
- **Redis**: Celery broker + cache.
- **Celery worker**: ingest and geocode background jobs.
- **Mapbox**: primary on-demand directions/geocode.
- **ORS**: fallback/batch geocode path.

## Why these choices
- **Postgres/PostGIS over MongoDB**: stronger spatial SQL/indexing, relational constraints, deterministic decimal handling for price/cost.
- **Redis**: low-latency cache plus durable async task handoff.
- **Monolith-first layout (web + worker)**: simpler delivery while still showing production patterns (async jobs, cache, geospatial DB).

## File upload + progressive geocode
- Upload endpoint is suitable for daily price-file changes.
- Processing is async: upload -> ingestion record -> Redis queue -> worker upsert.
- Geocode mode is env-switchable:
  - `INGEST_GEOCODE=False`: fastest ingest, allows `geom=NULL`.
  - `INGEST_GEOCODE=True`: geocode while ingesting (slower, can hit basic-tier rate limits).

### Backfill behavior (technical)
- Worker task: `geocode_pending(batch_size=5000)` (tunable).
- Selector: `FuelStation.objects.filter(geom__isnull=True)[:batch_size]`.
- Per-row flow: normalize address -> geocode -> update `geom` on success.
- Failed rows remain null and are retried in later batches.
- Already geocoded rows are skipped by filter (idempotent repeated runs).
- Result: fast initial availability + progressive convergence to full geocode coverage.

## Routing algorithm
- Build candidate nodes: virtual `start`, virtual `end`, and corridor stations.
- Add edge `A -> B` only if `distance(A,B) <= VEHICLE_MAX_RANGE_MILES`.
- Edge cost: `distance(A,B) / VEHICLE_MPG * price_at_A`.
- Run Dijkstra to minimize total fuel cost.
- For trips within max range, direct path is used and `fuel_stops` can be empty while cost remains non-zero.

## Configuration reference

### Vehicle + optimization
- `VEHICLE_MAX_RANGE_MILES` - maximum drivable distance per leg before refuel (default: `500`)
- `VEHICLE_MPG` - fuel efficiency used in cost math (default: `10`)

### Provider selection + endpoints
- `MAPBOX_API_KEY` - primary provider key for on-demand route/geocode
- `ORS_API_KEY` - fallback/batch provider key
- `MAPBOX_DIRECTIONS_BASE_URL` - Mapbox directions endpoint
- `ORS_DIRECTIONS_URL` - ORS directions endpoint
- `MAPBOX_GEOCODING_BASE_URL` - Mapbox geocoding endpoint
- `ORS_GEOCODING_URL` - ORS geocoding endpoint

### Ingest + geocode behavior
- `INGEST_GEOCODE=false` - fastest CSV load; allows `geom=NULL` and backfills later
- `INGEST_GEOCODE=true` - geocodes during ingest; can be slower/rate-limited on basic tiers

### HTTP performance tuning
- `HTTP_TIMEOUT_SECONDS` - per-call timeout budget (default: `3`)
- `MAPBOX_DIRECTIONS_MAX_ATTEMPTS` - retry budget for Mapbox directions (default: `2`)
- `ORS_DIRECTIONS_MAX_ATTEMPTS` - retry budget for ORS directions (default: `2`)
- `MAPBOX_GEOCODE_MAX_ATTEMPTS` - retry budget for Mapbox geocode (default: `2`)
- `ORS_GEOCODE_MAX_ATTEMPTS` - retry budget for ORS geocode (default: `2`)

### Example env block
```env
MAPBOX_API_KEY=your_mapbox_key
ORS_API_KEY=your_ors_key

VEHICLE_MAX_RANGE_MILES=500
VEHICLE_MPG=10
INGEST_GEOCODE=False

HTTP_TIMEOUT_SECONDS=3
MAPBOX_DIRECTIONS_MAX_ATTEMPTS=2
ORS_DIRECTIONS_MAX_ATTEMPTS=2
MAPBOX_GEOCODE_MAX_ATTEMPTS=2
ORS_GEOCODE_MAX_ATTEMPTS=2
```

## Performance notes
- Baseline cold route: ~4.0s.
- Current cold route: ~900ms (observed).
- Changes:
  - Mapbox kept as primary path.
  - Shared `requests.Session` for connection reuse.
  - Timeout/retry capped via env (default attempts = 2).
- Trade-off: tighter timeout/retry can increase failure probability during upstream instability, but reduces latency tail.
