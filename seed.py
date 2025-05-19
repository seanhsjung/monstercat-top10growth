import os
import time
import requests
import psycopg2

# ▸ 1. Read DATABASE_URL
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("⚠️  Set the DATABASE_URL env var before running (export DATABASE_URL=…)")

# ▸ 2. Connect to Postgres
conn = psycopg2.connect(db_url)
cur  = conn.cursor()

API    = "https://player.monstercat.app/api/artists"
offset = 0
limit  = 100  # (Monstercat allows up to 400)

# ▸ 3. Fetch total count
resp = requests.get(API, params={"limit": 1, "offset": 0})
resp.raise_for_status()
total = resp.json()["Artists"]["Total"]
print(f"Total artists to fetch: {total}")

# ▸ 4. Loop with debug prints
while offset < total:
    resp = requests.get(API, params={"limit": limit, "offset": offset})
    resp.raise_for_status()
    batch = resp.json()["Artists"]["Data"]

    for artist in batch:
        cur.execute(
            """
            INSERT INTO artists(id, name, uri)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (artist["Id"], artist["Name"], artist["URI"])
        )
    conn.commit()
    print(f"✔️  Inserted {len(batch)} artists (offset now {offset + len(batch)})")

    offset += limit
    time.sleep(1)   # back to 1 req/sec

print("🎉 Debug seeding complete!")
cur.close()
conn.close()