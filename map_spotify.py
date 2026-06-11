#!/usr/bin/env python3
import os
import sys
import csv
import json
import logging
from sqlalchemy import create_engine, MetaData, Table, select, update
from spotify_helper import search_artist_exact, fetch_monstercat_spotify_links

# ─── Config & Logging ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ─── Paths & Env ───────────────────────────────────────────────────────────────
DATABASE_URL    = os.getenv("DATABASE_URL")
MANUAL_JSON     = "manual_mappings.json"
SKIPPED_CSV     = "skipped_artists.csv"

if not DATABASE_URL:
    logger.error("Set DATABASE_URL env var (e.g. postgres://...)" )
    sys.exit(1)

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    # 1) load manual overrides keyed by DB ID (Tier 1 - highest priority)
    try:
        with open(MANUAL_JSON, "r") as f:
            overrides: dict[str, str] = json.load(f)
    except FileNotFoundError:
        logger.error(
            f"{MANUAL_JSON} not found. Fill it with your manual "
            "{db_id: spotify_id} pairs first."
        )
        sys.exit(1)

    # 2) fetch Monstercat artist profile Spotify links (Tier 2)
    logger.info("Fetching Monstercat artist profiles for direct Spotify links…")
    mc_links = fetch_monstercat_spotify_links()
    logger.info(f"Found {len(mc_links)} Monstercat artists with a valid direct Spotify link.")

    # 3) connect & reflect
    engine   = create_engine(DATABASE_URL, future=True)
    metadata = MetaData()
    artists  = Table("artists", metadata, autoload_with=engine)

    # 4) pull all artists needing a spotify_id
    with engine.begin() as conn:
        to_map = conn.execute(
            select(artists.c.id, artists.c.name)
            .where(artists.c.spotify_id.is_(None))
        ).all()

    total = len(to_map)
    logger.info(f"Mapping {total} artists → Spotify…")

    tier_counts  = {"manual": 0, "links": 0, "search": 0, "unresolved": 0}
    skipped_rows = []

    # 5) iterate & upsert
    for idx, (db_id, name) in enumerate(to_map, 1):
        key  = str(db_id)
        sid  = None
        tier = None

        # 5a) Tier 1: manual override by DB id
        if key in overrides:
            sid, tier = overrides[key], "manual"

        # 5b) Tier 2: Monstercat profile Spotify link
        elif key in mc_links:
            sid, tier = mc_links[key], "links"

        # 5c) Tier 3: Spotify search fallback
        else:
            candidate = search_artist_exact(name)
            if candidate:
                sid, tier = candidate, "search"

        if sid:
            tier_counts[tier] += 1
            logger.info(f"[{idx}/{total}] '{name}' (#{db_id}) -> {sid} (tier={tier})")
            with engine.begin() as conn:
                conn.execute(
                    update(artists)
                    .where(artists.c.id == db_id)
                    .values(spotify_id=sid)
                )
        else:
            tier_counts["unresolved"] += 1
            logger.warning(f"[{idx}/{total}] ⚠️ No Spotify match for '{name}' (#{db_id}), skipping")
            skipped_rows.append({"db_id": db_id, "name": name})

    # 6) write skipped artists for visibility (only if non-empty)
    if skipped_rows:
        with open(SKIPPED_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["db_id", "name"])
            writer.writeheader()
            writer.writerows(skipped_rows)
        logger.info(f"Wrote {len(skipped_rows)} unresolved artists to {SKIPPED_CSV}")

    logger.info(
        f"Done. manual={tier_counts['manual']} "
        f"links={tier_counts['links']} "
        f"search={tier_counts['search']} "
        f"unresolved={tier_counts['unresolved']} "
        f"(total={total})"
    )

if __name__ == "__main__":
    main()
