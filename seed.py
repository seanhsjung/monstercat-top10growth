import os
import time
import requests
import psycopg2
from psycopg2.extras import execute_values

API   = "https://player.monstercat.app/api/artists"
LIMIT = 100


def fetch_roster() -> list[tuple[str, str, str]]:
    """Paginate MC /api/artists → list of (id, name, uri)."""
    resp = requests.get(API, params={"limit": 1, "offset": 0})
    resp.raise_for_status()
    total = resp.json()["Artists"]["Total"]
    print(f"Total artists to fetch: {total}")

    artists = []
    offset = 0
    while offset < total:
        resp = requests.get(API, params={"limit": LIMIT, "offset": offset})
        resp.raise_for_status()
        batch = resp.json()["Artists"]["Data"]
        artists.extend((a["Id"], a["Name"], a["URI"]) for a in batch)
        print(f"✔️  Fetched {len(batch)} artists (offset {offset} → {offset + len(batch)})")
        offset += len(batch)
        time.sleep(1)
    return artists


def upsert_artists(conn, artists: list[tuple]) -> list[tuple[str, str]]:
    """INSERT ... ON CONFLICT DO NOTHING RETURNING id, name.
    Returns (id, name) for each row actually inserted (not conflicted)."""
    if not artists:
        return []
    with conn.cursor() as cur:
        new_rows = execute_values(
            cur,
            """
            INSERT INTO artists(id, name, uri)
            VALUES %s
            ON CONFLICT DO NOTHING
            RETURNING id, name
            """,
            artists,
            fetch=True,
        )
    conn.commit()
    return new_rows


if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("⚠️  Set the DATABASE_URL env var before running (export DATABASE_URL=…)")

    conn = psycopg2.connect(db_url)
    roster = fetch_roster()
    new_rows = upsert_artists(conn, roster)
    print(f"Inserted {len(new_rows)} new artists (of {len(roster)} fetched).")
    conn.close()
    print("🎉 Seeding complete!")
