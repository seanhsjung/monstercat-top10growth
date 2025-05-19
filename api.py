from fastapi import FastAPI, WebSocket
import asyncpg
import os
import asyncio

app = FastAPI()
DATABASE_URL = os.getenv("DATABASE_URL")

# Helper to fetch the last 24 h of metrics for a given artist
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
        aid
    )
    await conn.close()
    # convert to list of dicts for JSON
    return [dict(r) for r in rows]

@app.get("/artist/{aid}/latest")
async def latest(aid: str):
    return await fetch_latest(aid)

@app.get("/artists")
async def list_artists():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT id, name FROM artists ORDER BY name")
    await conn.close()
    return [dict(r) for r in rows]

@app.websocket("/ws/{aid}")
async def ws_endpoint(ws: WebSocket, aid: str):
    await ws.accept()
    while True:
        data = await fetch_latest(aid)
        await ws.send_json(data)
        await asyncio.sleep(60)  # push updates every minute
