#!/usr/bin/env python3
import os
import sys
import json
import logging
from sqlalchemy import create_engine, MetaData, Table, select, update
from spotify_helper import search_artist_exact

# ─── Config & Logging ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ─── Paths & Env ───────────────────────────────────────────────────────────────
DATABASE_URL    = os.getenv("DATABASE_URL")
MANUAL_JSON     = "manual_mappings.json"

if not DATABASE_URL:
    logger.error("Set DATABASE_URL env var (e.g. postgres://...)" )
    sys.exit(1)

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    # 1) load manual overrides keyed by DB ID
    try:
        with open(MANUAL_JSON, "r") as f:
            overrides: dict[str, str] = json.load(f)
    except FileNotFoundError:
        logger.error(
            f"{MANUAL_JSON} not found. Fill it with your manual "
            "{db_id: spotify_id} pairs first."
        )
        sys.exit(1)

    # 2) connect & reflect
    engine   = create_engine(DATABASE_URL, future=True)
    metadata = MetaData()
    artists  = Table("artists", metadata, autoload_with=engine)

    # 3) pull all artists needing a spotify_id
    with engine.begin() as conn:
        to_map = conn.execute(
            select(artists.c.id, artists.c.name)
            .where(artists.c.spotify_id.is_(None))
        ).all()

    total = len(to_map)
    logger.info(f"Mapping {total} artists → Spotify…")

    # 4) iterate & upsert
    for idx, (db_id, name) in enumerate(to_map, 1):
        # 4a) check manual override by DB id
        key = str(db_id)
        if key in overrides:
            sid = overrides[key]
            logger.info(f"[{idx}/{total}] '{name}' (#{db_id}) manual‐mapped → {sid}")
            with engine.begin() as conn:
                conn.execute(
                    update(artists)
                    .where(artists.c.id == db_id)
                    .values(spotify_id=sid)
                )
            continue

        # 4b) otherwise, hit Spotify
        logger.info(f"[{idx}/{total}] searching '{name}'…")
        sid = search_artist_exact(name)
        if not sid:
            logger.warning(f"[{idx}/{total}] ⚠️ No Spotify match for '{name}', skipping")
            continue

        # 4c) write it back
        logger.info(f"[{idx}/{total}] → {sid}")
        with engine.begin() as conn:
            conn.execute(
                update(artists)
                .where(artists.c.id == db_id)
                .values(spotify_id=sid)
            )

    logger.info("Done.")

if __name__ == "__main__":
    main()
