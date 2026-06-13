import os
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

@app.on_event("startup")
async def log_db_url():
    print(f"[STARTUP] Using DATABASE_URL = {DATABASE_URL}")

# ─── Helper: fetch last 24h of metrics for an artist ────────────────────────────
async def fetch_latest(aid: str):
    conn = await asyncpg.connect(DATABASE_URL)
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
    await conn.close()
    return [dict(r) for r in rows]

# ────────────────────────────────────────────────────────────────────────────────
# Existing endpoint: list all artists
@app.get("/artists")
async def list_artists():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT id, name FROM artists ORDER BY name")
    await conn.close()
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
    conn = await asyncpg.connect(DATABASE_URL)

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

    await conn.close()
    return [dict(r) for r in rows]

# ────────────────────────────────────────────────────────────────────────────────
# Existing: Top‐growth endpoint (unchanged)
@app.get("/artists/top-growth")
async def top_growth(period: str = "7 days", limit: int = 10):
    # Debug inputs
    print(f"[DEBUG] top_growth called with period={period!r}, limit={limit!r}")

    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be 1–100")

    if period.lower() == "all":
        query = """
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
          (w_max.followers - w_min.followers) AS delta
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
          (latest.followers - baseline.followers) AS delta
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

    print("[DEBUG] Executing SQL:", query.replace("\n", " "))

    conn = await asyncpg.connect(DATABASE_URL)
    count_row = await conn.fetchrow("SELECT COUNT(*) AS c FROM metrics")
    print(f"[DEBUG] metrics table has {count_row['c']} rows")

    rows = await conn.fetch(query, limit)
    await conn.close()

    print(f"[DEBUG] top_growth returned {len(rows)} rows")
    print("[DEBUG] sample rows:", rows[:5])

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

    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch(query, limit)
    await conn.close()

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
