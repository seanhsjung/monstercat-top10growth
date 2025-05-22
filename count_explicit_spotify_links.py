#!/usr/bin/env python3
import os
import requests
import psycopg2

API_BASE = "https://player.monstercat.app/api/artists"
DB_URL   = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("Set DATABASE_URL before running")

def has_spotify_link(uri):
    try:
        resp = requests.get(f"{API_BASE}/{uri}", timeout=5)
    except requests.RequestException:
        return False

    if resp.status_code != 200:
        return False

    try:
        payload = resp.json()
    except ValueError:
        # not valid JSON
        return False

    data = payload.get("Artists", {}).get("Data", [])
    if not data:
        return False

    links = data[0].get("Links", [])
    return any(l.get("Platform","").lower() == "spotify" for l in links)

def main():
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()
    cur.execute("SELECT uri, name FROM artists;")
    rows = cur.fetchall()

    total = len(rows)
    count_with = 0
    examples = []

    for uri, name in rows:
        if has_spotify_link(uri):
            count_with += 1
            if len(examples) < 10:
                examples.append((name, uri))

    cur.close()
    conn.close()

    print(f"{count_with}/{total} artists have an explicit Spotify link.")
    print("Sample with links:")
    for name, uri in examples:
        print(f" • {name} (slug: {uri})")

if __name__ == "__main__":
    main()
