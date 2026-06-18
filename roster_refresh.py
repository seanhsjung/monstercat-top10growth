#!/usr/bin/env python3
"""
Weekly Monstercat roster refresh.

Fetches the current Monstercat artist roster, inserts any new artists into
the database, and attempts Spotify mapping for newly inserted artists only.
Existing artist records and Spotify mappings are never modified.
"""
import json
import logging
import os

import psycopg2

from seed import fetch_roster, upsert_artists

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL env var before running")

MANUAL_JSON = "manual_mappings.json"


def load_manual_overrides() -> dict[str, str]:
    try:
        with open(MANUAL_JSON) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"{MANUAL_JSON} not found — skipping Tier 1 manual overrides")
        return {}


def map_new_artists(
    conn, new_artists: list[tuple[str, str]]
) -> tuple[list[str], list[str]]:
    """
    Run 3-tier Spotify mapping for each (id, name) in new_artists.
    Writes spotify_id to DB for successful matches.
    Returns (mapped_names, unmapped_names).
    """
    from spotify_helper import fetch_monstercat_spotify_links, search_artist_exact

    overrides = load_manual_overrides()
    mc_links  = fetch_monstercat_spotify_links()

    mapped:   list[str] = []
    unmapped: list[str] = []

    for artist_id, name in new_artists:
        sid = tier = None

        if artist_id in overrides:
            sid, tier = overrides[artist_id], "manual"
        elif artist_id in mc_links:
            sid, tier = mc_links[artist_id], "links"
        else:
            candidate = search_artist_exact(name)
            if candidate:
                sid, tier = candidate, "search"

        if sid:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE artists SET spotify_id = %s WHERE id = %s",
                    (sid, artist_id),
                )
            conn.commit()
            logger.info(f"  ✔ {name} → {sid} ({tier})")
            mapped.append(name)
        else:
            logger.info(f"  ✘ {name} — no match found")
            unmapped.append(name)

    return mapped, unmapped


def print_summary(
    fetched: int,
    new_artists: list[tuple[str, str]],
    mapped: list[str],
    unmapped: list[str],
) -> None:
    new_names = [name for _, name in new_artists]

    print("\nRoster refresh complete\n")
    print(f"  Fetched:       {fetched:>6,} artists")
    print(f"  New artists:   {len(new_artists):>6}")

    if new_names:
        # Wrap names at ~72 chars
        line, lines = "    ", []
        for i, name in enumerate(new_names):
            sep = ", " if i < len(new_names) - 1 else ""
            if len(line) + len(name) + len(sep) > 72 and line.strip():
                lines.append(line.rstrip(", "))
                line = "    " + name + sep
            else:
                line += name + sep
        if line.strip():
            lines.append(line)
        print("\n".join(lines))

    if new_artists:
        print()
        print("  Spotify mapping:")
        if mapped:
            print(f"    Mapped   ({len(mapped):>2}):  " + ", ".join(mapped))
        if unmapped:
            print(f"    Unmapped ({len(unmapped):>2}):  " + ", ".join(unmapped) + "  ← manual review required")


def main():
    conn         = psycopg2.connect(DATABASE_URL)
    roster       = fetch_roster()
    new_artists  = upsert_artists(conn, roster)

    if not new_artists:
        print_summary(len(roster), [], [], [])
        conn.close()
        return

    mapped, unmapped = map_new_artists(conn, new_artists)
    conn.close()
    print_summary(len(roster), new_artists, mapped, unmapped)


if __name__ == "__main__":
    main()
