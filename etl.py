#!/usr/bin/env python3
"""
ETL script for Monstercat Top10 Growth demo.
Connects to Postgres, ensures schema, and batch-fetches Spotify metrics,
upserting into the metrics table using Monstercat artist IDs.
"""
import os
import time
import math
import logging
import requests
import psycopg2
from psycopg2.extras import execute_values
from spotify_helper import get_token

# ── Logging ─────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────────
DATABASE_URL   = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("⚠️  Set the DATABASE_URL env var before running ETL")

RATE_LIMIT_QPS = float(os.getenv("RATE_LIMIT_QPS", "1"))
BATCH_SIZE     = int(os.getenv("BATCH_SIZE", "50"))

# ── Helpers ─────────────────────────────────────────────────────────────────────
def ensure_schema(conn):
    """
    Create artists & metrics tables if they don't exist.
    """
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS artists(
          id           TEXT PRIMARY KEY,
          name         TEXT,
          uri          TEXT,
          spotify_id   TEXT
        );
        CREATE TABLE IF NOT EXISTS metrics(
          artist_id TEXT,
          source    TEXT,
          metric    TEXT,
          ts        TIMESTAMPTZ DEFAULT now(),
          val       NUMERIC,
          PRIMARY KEY (artist_id, source, metric, ts)
        );
        """)
    conn.commit()

def upsert_metrics(conn, rows):
    """
    Bulk upsert a list of (artist_id, source, metric, val) into metrics.
    """
    if not rows:
        return
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO metrics (artist_id, source, metric, val)
            VALUES %s
            ON CONFLICT (artist_id, source, metric, ts) DO NOTHING
            """,
            rows
        )
    conn.commit()

def fetch_artists(conn):
    """
    Return list of (mc_id, spotify_id) for all artists mapped to Spotify.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, spotify_id FROM artists WHERE spotify_id IS NOT NULL"
        )
        return cur.fetchall()

def fetch_spotify_batch(token, spotify_ids):
    """
    Call Spotify's batch-artists endpoint for up to 50 IDs.
    Returns list of artist dicts (or None for unknown IDs), in the same order.
    """
    headers = {"Authorization": f"Bearer {token}"}
    url     = "https://api.spotify.com/v1/artists"
    params  = {"ids": ",".join(spotify_ids)}
    resp    = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json().get("artists", [])

# ── Main ETL ────────────────────────────────────────────────────────────────────
def main():
    # 1) Connect to Postgres and ensure tables exist
    conn = psycopg2.connect(DATABASE_URL)
    ensure_schema(conn)

    # 2) Fetch all artists with a Spotify ID
    artist_rows = fetch_artists(conn)  # List of (mc_id, sp_id)
    total       = len(artist_rows)
    batches     = math.ceil(total / BATCH_SIZE)
    logger.info(f"Will process {total} artists in {batches} batches of up to {BATCH_SIZE}")

    if total == 0:
        logger.info("No artists to process. Have you seeded and mapped Spotify IDs?")
        return

    # 3) Get a fresh Spotify token
    token = get_token()

    # 4) Process in batches
    for batch_num in range(batches):
        start = batch_num * BATCH_SIZE
        end   = start + BATCH_SIZE
        batch = artist_rows[start:end]
        spotify_ids = [sp for _, sp in batch]

        # Fetch the batch
        artists_data = fetch_spotify_batch(token, spotify_ids)

        # Build a map back to your MC IDs
        id_map = {sp: mc for mc, sp in batch}

        metrics_to_insert = []
        # Zip so we know which ID gave us None
        for requested_id, sp_artist in zip(spotify_ids, artists_data):
            if sp_artist is None:
                logger.warning(f"⚠️  Spotify returned null for ID {requested_id}; skipping.")
                continue

            spid = sp_artist.get("id")
            if spid != requested_id:
                logger.warning(f"⚠️  Spotify returned unexpected ID {spid} vs requested {requested_id}")

            mc_id = id_map.get(requested_id)
            if not mc_id:
                logger.error(f"⚠️  No MC mapping found for {requested_id}; skipping.")
                continue

            followers  = sp_artist["followers"]["total"]
            popularity = sp_artist.get("popularity", 0)

            metrics_to_insert.extend([
                (mc_id, "spotify", "followers",  followers),
                (mc_id, "spotify", "popularity", popularity),
            ])

        # Upsert into Postgres
        upsert_metrics(conn, metrics_to_insert)
        logger.info(f"✔️  Inserted metrics for {len(metrics_to_insert)//2} artists (batch {batch_num+1}/{batches})")

        # Rate-limit to ~1 request/sec
        time.sleep(1 / RATE_LIMIT_QPS)

    conn.close()
    logger.info("🎉 ETL complete!")

if __name__ == "__main__":
    main()
