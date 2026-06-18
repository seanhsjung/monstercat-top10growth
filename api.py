import os
import re
import asyncio
import asyncpg
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ─── CORS setup ────────────────────────────────────────────────────────────────
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Database URL ───────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set the DATABASE_URL env var before running")

# ─── Shared connection pool ──────────────────────────────────────────────────
pool: asyncpg.Pool | None = None

@app.on_event("startup")
async def startup():
    global pool
    # statement_cache_size=0: required for Neon's pgbouncer pooler endpoint,
    # which runs in transaction-pooling mode and doesn't support asyncpg's
    # per-connection prepared statement cache.
    pool = await asyncpg.create_pool(
        DATABASE_URL, statement_cache_size=0, min_size=1, max_size=10
    )
    print(f"[STARTUP] Using DATABASE_URL = {DATABASE_URL}")

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

# ─── Helper: fetch last 24h of metrics for an artist ────────────────────────────
async def fetch_latest(aid: str):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT metric, val, ts
              FROM metrics
             WHERE artist_id = $1
               AND ts > now() - INTERVAL '24 hours'
             ORDER BY ts
            """,
            aid,
        )
    return [dict(r) for r in rows]

# ────────────────────────────────────────────────────────────────────────────────
# Existing endpoint: list all artists
@app.get("/artists")
async def list_artists():
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, name FROM artists ORDER BY name")
    return [dict(r) for r in rows]

# ────────────────────────────────────────────────────────────────────────────────
# Existing endpoint: latest 24h metrics for one artist
@app.get("/artist/{aid}/latest")
async def latest(aid: str):
    data = await fetch_latest(aid)
    return data or []

# ────────────────────────────────────────────────────────────────────────────────
# NEW: “metrics over arbitrary period” endpoint
#    - e.g. GET /artist/{aid}/metrics?period=7 days     OR
#            GET /artist/{aid}/metrics?period=all
#
#    Query parameters:
#      * period = "24 hours" (default)   OR
#      * period = "3 days", "7 days", "30 days", ..., "all"
#
@app.get("/artist/{aid}/metrics")
async def metrics(aid: str, period: str = "24 hours"):
    async with pool.acquire() as conn:
        # If the user wants “all time,” don’t filter by ts
        if period.lower() == "all":
            rows = await conn.fetch(
                """
                SELECT metric, val, ts
                  FROM metrics
                 WHERE artist_id = $1
                   AND source = 'spotify'
                   AND metric = 'followers'
                 ORDER BY ts
                """,
                aid,
            )
        else:
            # Otherwise subtract “period” from now()
            # (e.g. INTERVAL '7 days', INTERVAL '24 hours', INTERVAL '30 days')
            query = f"""
            SELECT metric, val, ts
              FROM metrics
             WHERE artist_id = $1
               AND source = 'spotify'
               AND metric = 'followers'
               AND ts >= now() - INTERVAL '{period}'
             ORDER BY ts
            """
            rows = await conn.fetch(query, aid)

    return [dict(r) for r in rows]

# ────────────────────────────────────────────────────────────────────────────────
# NEW: per-artist growth summary, for KPI cards on the Artist Detail page
#    - GET /artist/{aid}/growth?period=24 hours   (default)
#    - returns one entry per metric present for this artist under source='spotify'
#      (e.g. "followers", "popularity", ...), each shaped like:
#        {"latest_value": ..., "baseline_value": ..., "absolute_delta": ..., "percent_delta": ...}
_PERIOD_RE = re.compile(r"^(?:all|\d+\s+(?:second|minute|hour|day|week|month|year)s?)$", re.IGNORECASE)

@app.get("/artist/{aid}/growth")
async def artist_growth(aid: str, period: str = "24 hours"):
    if not _PERIOD_RE.match(period):
        raise HTTPException(status_code=400, detail="invalid period")

    if period.lower() == "all":
        query = """
        WITH windowed AS (
          SELECT
            artist_id,
            metric,
            val,
            ts,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id, metric
              ORDER BY ts ASC
            ) AS rn_asc,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id, metric
              ORDER BY ts DESC
            ) AS rn_desc
          FROM metrics
          WHERE artist_id = $1
            AND source = 'spotify'
        )
        SELECT
          w_max.metric,
          w_max.val AS latest_value,
          w_min.val AS baseline_value,
          (w_max.val - w_min.val) AS absolute_delta,
          CASE WHEN w_min.val = 0 THEN NULL
               ELSE ROUND((w_max.val - w_min.val) / w_min.val::numeric * 100, 4)
          END AS percent_delta
        FROM windowed w_min
        JOIN windowed w_max
          ON w_min.artist_id = w_max.artist_id
         AND w_min.metric = w_max.metric
        WHERE w_min.rn_asc = 1
          AND w_max.rn_desc = 1;
        """
    else:
        query = f"""
        WITH latest AS (
          SELECT
            artist_id,
            metric,
            val,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id, metric
              ORDER BY ts DESC
            ) AS rn
          FROM metrics
          WHERE artist_id = $1
            AND source = 'spotify'
        ),
        baseline AS (
          SELECT
            artist_id,
            metric,
            val,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id, metric
              ORDER BY
                (ts <= now() - INTERVAL '{period}') DESC,
                CASE WHEN ts <= now() - INTERVAL '{period}' THEN ts END DESC,
                ts ASC
            ) AS rn
          FROM metrics
          WHERE artist_id = $1
            AND source = 'spotify'
        )
        SELECT
          latest.metric,
          latest.val AS latest_value,
          baseline.val AS baseline_value,
          (latest.val - baseline.val) AS absolute_delta,
          CASE WHEN baseline.val = 0 THEN NULL
               ELSE ROUND((latest.val - baseline.val) / baseline.val::numeric * 100, 4)
          END AS percent_delta
        FROM latest
        JOIN baseline
          ON latest.artist_id = baseline.artist_id
         AND latest.metric = baseline.metric
        WHERE latest.rn = 1
          AND baseline.rn = 1;
        """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, aid)

    return {
        row["metric"]: {
            "latest_value": row["latest_value"],
            "baseline_value": row["baseline_value"],
            "absolute_delta": row["absolute_delta"],
            "percent_delta": row["percent_delta"],
        }
        for row in rows
    }

# ────────────────────────────────────────────────────────────────────────────────
# Existing: Top‐growth endpoint (unchanged)
@app.get("/artists/top-growth")
async def top_growth(period: str = "7 days", limit: int = 10, sort_by: str = "absolute", mode: str = "all"):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be 1–100")
    if mode not in ("all", "discovery"):
        raise HTTPException(status_code=400, detail="mode must be 'all' or 'discovery'")
    if mode == "discovery":
        sort_by = "percent"
    elif sort_by not in ("absolute", "percent"):
        raise HTTPException(status_code=400, detail="sort_by must be 'absolute' or 'percent'")

    order_by = "absolute_delta DESC" if sort_by == "absolute" else "percent_delta DESC NULLS LAST"
    # discovery mode: filter to the 5k–250k follower band (applied in the final WHERE clause)
    discovery_clause_windowed = "AND w_max.followers BETWEEN 5000 AND 250000" if mode == "discovery" else ""
    discovery_clause_latest = "AND latest.followers BETWEEN 5000 AND 250000" if mode == "discovery" else ""

    if period.lower() == "all":
        query = f"""
        WITH windowed AS (
          SELECT
            artist_id,
            val AS followers,
            ts,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id
              ORDER BY ts ASC
            ) AS rn_asc,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id
              ORDER BY ts DESC
            ) AS rn_desc
          FROM metrics
          WHERE source='spotify'
            AND metric='followers'
        )
        SELECT
          a.id,
          a.name,
          w_max.followers AS latest_value,
          w_min.followers AS baseline_value,
          (w_max.followers - w_min.followers) AS absolute_delta,
          CASE WHEN w_min.followers = 0 THEN NULL
               ELSE ROUND((w_max.followers - w_min.followers) / w_min.followers::numeric * 100, 4)
          END AS percent_delta
        FROM windowed w_min
        JOIN windowed w_max
          ON w_min.artist_id = w_max.artist_id
        JOIN artists a
          ON a.id = w_min.artist_id
        WHERE w_min.rn_asc = 1
          AND w_max.rn_desc = 1
          {discovery_clause_windowed}
        ORDER BY {order_by}
        LIMIT $1;
        """
    else:
        # "latest" = most recent snapshot per artist.
        # "baseline" = most recent snapshot at/before `period` ago, falling
        # back to the earliest snapshot overall if none exists yet (not
        # enough history). delta = latest - baseline.
        query = f"""
        WITH latest AS (
          SELECT
            artist_id,
            val AS followers,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id
              ORDER BY ts DESC
            ) AS rn
          FROM metrics
          WHERE source='spotify'
            AND metric='followers'
        ),
        baseline AS (
          SELECT
            artist_id,
            val AS followers,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id
              ORDER BY
                (ts <= now() - INTERVAL '{period}') DESC,
                CASE WHEN ts <= now() - INTERVAL '{period}' THEN ts END DESC,
                ts ASC
            ) AS rn
          FROM metrics
          WHERE source='spotify'
            AND metric='followers'
        )
        SELECT
          a.id,
          a.name,
          latest.followers AS latest_value,
          baseline.followers AS baseline_value,
          (latest.followers - baseline.followers) AS absolute_delta,
          CASE WHEN baseline.followers = 0 THEN NULL
               ELSE ROUND((latest.followers - baseline.followers) / baseline.followers::numeric * 100, 4)
          END AS percent_delta
        FROM latest
        JOIN baseline
          ON latest.artist_id = baseline.artist_id
        JOIN artists a
          ON a.id = latest.artist_id
        WHERE latest.rn = 1
          AND baseline.rn = 1
          {discovery_clause_latest}
        ORDER BY {order_by}
        LIMIT $1;
        """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, limit)

    return [dict(r) for r in rows]

# ────────────────────────────────────────────────────────────────────────────────
# NEW: Top popularity-growth endpoint
@app.get("/artists/top-popularity-growth")
async def top_popularity_growth(period: str = "7 days", limit: int = 10):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be 1–100")

    if period.lower() == "all":
        query = """
        WITH windowed AS (
          SELECT
            artist_id,
            val AS popularity,
            ts,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id
              ORDER BY ts ASC
            ) AS rn_asc,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id
              ORDER BY ts DESC
            ) AS rn_desc
          FROM metrics
          WHERE source='spotify'
            AND metric='popularity'
        )
        SELECT
          a.id,
          a.name,
          w_min.popularity AS earliest_popularity,
          w_max.popularity AS latest_popularity,
          (w_max.popularity - w_min.popularity) AS delta
        FROM windowed w_min
        JOIN windowed w_max
          ON w_min.artist_id = w_max.artist_id
        JOIN artists a
          ON a.id = w_min.artist_id
        WHERE w_min.rn_asc = 1
          AND w_max.rn_desc = 1
        ORDER BY delta DESC
        LIMIT $1;
        """
    else:
        # "latest" = most recent snapshot per artist.
        # "baseline" = most recent snapshot at/before `period` ago, falling
        # back to the earliest snapshot overall if none exists yet (not
        # enough history). delta = latest - baseline.
        query = f"""
        WITH latest AS (
          SELECT
            artist_id,
            val AS popularity,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id
              ORDER BY ts DESC
            ) AS rn
          FROM metrics
          WHERE source='spotify'
            AND metric='popularity'
        ),
        baseline AS (
          SELECT
            artist_id,
            val AS popularity,
            ROW_NUMBER() OVER (
              PARTITION BY artist_id
              ORDER BY
                (ts <= now() - INTERVAL '{period}') DESC,
                CASE WHEN ts <= now() - INTERVAL '{period}' THEN ts END DESC,
                ts ASC
            ) AS rn
          FROM metrics
          WHERE source='spotify'
            AND metric='popularity'
        )
        SELECT
          a.id,
          a.name,
          baseline.popularity AS earliest_popularity,
          latest.popularity AS latest_popularity,
          (latest.popularity - baseline.popularity) AS delta
        FROM latest
        JOIN baseline
          ON latest.artist_id = baseline.artist_id
        JOIN artists a
          ON a.id = latest.artist_id
        WHERE latest.rn = 1
          AND baseline.rn = 1
        ORDER BY delta DESC
        LIMIT $1;
        """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, limit)

    return [dict(r) for r in rows]

# ────────────────────────────────────────────────────────────────────────────────
# Existing: WebSocket endpoint (unchanged)
@app.websocket("/ws/{aid}")
async def ws_endpoint(websocket: WebSocket, aid: str):
    await websocket.accept()
    try:
        while True:
            data = await fetch_latest(aid)
            await websocket.send_json(data)
            await asyncio.sleep(60)
    except Exception:
        await websocket.close()
