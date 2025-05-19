import os
import time
import psycopg2
from spotify_helper import search_artist

db_url = os.getenv("DATABASE_URL")
conn   = psycopg2.connect(db_url)
cur    = conn.cursor()

# Select artists without a Spotify ID
cur.execute("SELECT id, name FROM artists WHERE spotify_id IS NULL")
rows = cur.fetchall()

print(f"Mapping {len(rows)} artists to Spotify...")
for artist_id, name in rows:
    sid = search_artist(name)
    if sid:
        cur.execute(
            "UPDATE artists SET spotify_id = %s WHERE id = %s",
            (sid, artist_id)
        )
        conn.commit()
        print(f" → {name!r} mapped to {sid}")
    else:
        print(f" ⚠️  No match for {name!r}")
    time.sleep(1)  # keep to 1 req/sec

cur.close()
conn.close()
print("Mapping complete.")
