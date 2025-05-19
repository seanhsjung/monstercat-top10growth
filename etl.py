#!/usr/bin/env python3
import os
import time
import math
import requests
import psycopg2
from psycopg2.extras import execute_values
from spotify_helper import get_token

# ── Configuration ────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("⚠️  Set the DATABASE_URL env var before running ETL")

RATE_LIMIT_QPS = float(os.getenv("RATE_LIMIT_QPS", "1"))
BATCH_SIZE = 50
SPOTIFY_TOKEN = None

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
    with conn.cursor() as cur:
        execute_values(cur,
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
    Return list of (id, spotify_id) for all artists mapped to Spotify.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, spotify_id
              FROM artists
             WHERE spotify_id IS NOT NULL
        """)
        return cur.fetchall()

def fetch_spotify_batch(token, spotify_ids):
    """
    Call Spotify's batch-artist endpoint for up to 50 IDs.
    Returns list of artist dicts.
    """
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://api.spotify.com/v1/artists"
    params = {"ids": ",".join(spotify_ids)}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json().get("artists", [])

# ── Main ETL ────────────────────────────────────────────────────────────────────

def main():
    global SPOTIFY_TOKEN

    # 1) Connect to Postgres and ensure tables exist
    conn = psycopg2.connect(DATABASE_URL)
    ensure_schema(conn)

    # 2) Fetch all artists with a Spotify ID
    artist_rows = fetch_artists(conn)
    total = len(artist_rows)
    print(f"Will process {total} artists in {math.ceil(total/BATCH_SIZE)} batches of up to {BATCH_SIZE}")

    # 3) Get a fresh Spotify token
    SPOTIFY_TOKEN = get_token()

    # 4) Process in batches
    for i in range(0, total, BATCH_SIZE):
        batch = artist_rows[i : i + BATCH_SIZE]
        spotify_ids = [sid for _, sid in batch]

        artists_data = fetch_spotify_batch(SPOTIFY_TOKEN, spotify_ids)

        # Collect metrics rows: (artist_id, source, metric, val)
        metrics_to_insert = []
        for artist in artists_data:
            aid = artist["id"]
            followers = artist["followers"]["total"]
            popularity = artist["popularity"]
            metrics_to_insert.append((aid, "spotify", "followers", followers))
            metrics_to_insert.append((aid, "spotify", "popularity", popularity))

        # Upsert into Postgres
        upsert_metrics(conn, metrics_to_insert)
        print(f"✔️  Inserted metrics for {len(batch)} artists (batch {i//BATCH_SIZE + 1})")

        # Rate‐limit to ~1 request/sec
        time.sleep(1 / RATE_LIMIT_QPS)

    conn.close()
    print("🎉 ETL complete!")

if __name__ == "__main__":
    main()
