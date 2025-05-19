import os
import time
import psycopg2
import requests
from spotify_helper import get_token

# 1. Read your DATABASE_URL
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("Set DATABASE_URL env var before running")

# 2. Connect to Postgres
conn = psycopg2.connect(db_url)
cur  = conn.cursor()

# 3. Fetch all (artist_id, spotify_id) pairs
cur.execute("SELECT id, spotify_id FROM artists WHERE spotify_id IS NOT NULL")
rows = cur.fetchall()  # List of tuples: [(artist_id, spid), ...]

# 4. Chunk into batches of 50
batch_size = 50
chunks = [rows[i : i + batch_size] for i in range(0, len(rows), batch_size)]
print(f"Will process {len(rows)} artists in {len(chunks)} batches of up to {batch_size}")

# 5. Loop over each batch
for idx, chunk in enumerate(chunks, start=1):
    # Build the comma-separated Spotify IDs
    spids = [spid for (_, spid) in chunk]
    ids_param = ",".join(spids)

    # Fetch in one request
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        "https://api.spotify.com/v1/artists",
        params={"ids": ids_param},
        headers=headers
    )
    resp.raise_for_status()
    artists_data = resp.json()["artists"]  # list of up to 50 artist objects

    # Upsert metrics for each artist in this batch
    for artist_obj, (artist_id, _) in zip(artists_data, chunk):
        followers  = artist_obj["followers"]["total"]
        popularity = artist_obj["popularity"]

        cur.execute(
            """
            INSERT INTO metrics(artist_id, source, metric, val)
            VALUES (%s, 'spotify', 'followers', %s)
            ON CONFLICT (artist_id, source, metric, ts) DO NOTHING
            """,
            (artist_id, followers)
        )
        cur.execute(
            """
            INSERT INTO metrics(artist_id, source, metric, val)
            VALUES (%s, 'spotify', 'popularity', %s)
            ON CONFLICT (artist_id, source, metric, ts) DO NOTHING
            """,
            (artist_id, popularity)
        )

    conn.commit()
    print(f"✔️  Batch {idx}/{len(chunks)}: processed {len(chunk)} artists")
    time.sleep(1)   # one batch/sec → ~20 s total for 1,019 artists

cur.close()
conn.close()
print("ETL run complete.")
