#!/usr/bin/env python3
import os, time
import requests
from spotify_helper import get_token

# ——— Configuration ———
SPOT_ID = "64KEffDW9EtZ1y2vBYgq8T"   # replace with the ID you just copied

# You can also export these in your shell instead of hard-coding:
os.environ["SPOTIFY_CLIENT_ID"]     = "<your-client-id>"
os.environ["SPOTIFY_CLIENT_SECRET"] = "<your-client-secret>"

# ——— Helpers ———
def fetch_followers(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}"
    resp = requests.get(url, headers={"Authorization":f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()["followers"]["total"]

# ——— Main ———
if __name__ == "__main__":
    # 1) Get an OAuth token
    token = get_token()

    # 2) First snapshot
    first = fetch_followers(token, SPOT_ID)
    print(f"[{time.strftime('%X')}] First snapshot for {SPOT_ID}: {first}")

    # 3) Wait some time (choose 5–15 minutes)
    wait_secs = 300  # 5 minutes
    print(f"Waiting {wait_secs//60} minutes…")
    time.sleep(wait_secs)

    # 4) Refresh token & take second snapshot
    token = get_token()
    second = fetch_followers(token, SPOT_ID)
    print(f"[{time.strftime('%X')}] Second snapshot for {SPOT_ID}: {second}")

    # 5) Delta
    print("Delta:", second - first)
