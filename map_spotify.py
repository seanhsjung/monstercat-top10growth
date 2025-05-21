#!/usr/bin/env python3
import os
import csv
import json
from sqlalchemy import create_engine, MetaData, Table, select, update
from spotify_helper import search_artist_exact

# --- CONFIG ---
DATABASE_URL = os.getenv("DATABASE_URL")
MANUAL_MAP_FILE = "manual_mappings.json"
SKIPPED_CSV = "skipped_artists.csv"
# ---------------

def load_manual_mappings():
    if os.path.exists(MANUAL_MAP_FILE):
        with open(MANUAL_MAP_FILE, "r", encoding="utf8") as fh:
            return json.load(fh)
    return {}

def main():
    if not DATABASE_URL:
        print("❌  Set DATABASE_URL")
        return

    manual = load_manual_mappings()
    engine = create_engine(DATABASE_URL)
    meta = MetaData()
    meta.reflect(engine, only=["artists"])
    artists = meta.tables["artists"]

    skipped = []

    with engine.begin() as conn:
        rows = conn.execute(
            select(artists.c.id, artists.c.name)
            .where(artists.c.spotify_id == None)
        ).all()

        total = len(rows)
        print(f"Mapping {total} artists → Spotify…")

        for idx, (aid, name) in enumerate(rows, start=1):
            # 1) manual mapping check
            if str(aid) in manual:
                sid = manual[str(aid)]
                print(f"[{idx}/{total}] '{name}': manual‐mapped → {sid}")
            else:
                # 2) try exact
                try:
                    sid = search_artist_exact(name)
                except Exception:
                    print(f"[{idx}/{total}] '{name}': exact‐match HTTP error, skipping")
                    sid = None

            if sid:
                conn.execute(
                    update(artists)
                    .where(artists.c.id == aid)
                    .values(spotify_id=sid)
                )
                if str(aid) not in manual:
                    print(f"[{idx}/{total}] '{name}': mapped → {sid}")
            else:
                print(f"[{idx}/{total}] ⚠️ No Spotify match for '{name}', skipping")
                skipped.append((aid, name))

    # write out any skipped for manual review
    if skipped:
        with open(SKIPPED_CSV, "w", newline="", encoding="utf8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["id", "name"])
            writer.writerows(skipped)
        print(f"\n🔍  {len(skipped)} artists skipped—see {SKIPPED_CSV} to manually add their Spotify IDs.")
    else:
        print("\n✅  All artists mapped.")

if __name__ == "__main__":
    main()
