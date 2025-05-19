import os
import asyncio
import asyncpg
from fastapi import FastAPI, WebSocket, HTTPException

app = FastAPI()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set the DATABASE_URL env var before running")

# Helper: fetch last 24h of metrics for an artist
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

@app.get("/artists")
async def list_artists():
    """
    Return a list of all artists (id + name), sorted alphabetically.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT id, name FROM artists ORDER BY name")
    await conn.close()
    return [dict(r) for r in rows]

@app.get("/artist/{aid}/latest")
async def latest(aid: str):
    """
    Return the last 24h of followers & popularity metrics for the given artist.
    """
    data = await fetch_latest(aid)
    if not data:
        # Could be no data yet or invalid artist
        return []
    return data

@app.get("/artists/top-growth")
async def top_growth(period: str = "7 days", limit: int = 10):
    """
    Return the top `limit` artists by Spotify follower growth over the past `period`.
    `period` must be a valid Postgres interval literal, e.g. '7 days' or '30 days'.
    """
    # Basic sanitization
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be 1–100")

    # Build the on-the-fly CTE query
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
        AND ts >= now() - INTERVAL '{period}'
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

    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch(query, limit)
    await conn.close()
    return [dict(r) for r in rows]

@app.websocket("/ws/{aid}")
async def ws_endpoint(websocket: WebSocket, aid: str):
    """
    WebSocket that pushes the latest 24h metrics for `aid` once per minute.
    """
    await websocket.accept()
    try:
        while True:
            data = await fetch_latest(aid)
            await websocket.send_json(data)
            await asyncio.sleep(60)
    except Exception:
        await websocket.close()
