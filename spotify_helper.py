import os
import requests

TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"

CLIENT_ID     = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

def get_token():
    resp = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def search_artist_exact(name: str):
    """
    Perform an exact artist search on Spotify:
    - Query up to 10 artists for the given name.
    - Return the first one whose artist["name"] exactly matches ours
      (case-insensitive).
    - If none match exactly, return None.
    """
    token = get_token()
    resp = requests.get(
        SEARCH_URL,
        headers={"Authorization": f"Bearer {token}"},
        params={"q": f'artist:"{name}"', "type": "artist", "limit": 10},
        timeout=5,
    )
    resp.raise_for_status()
    items = resp.json().get("artists", {}).get("items", [])
    lower_name = name.strip().lower()

    for artist in items:
        if artist["name"].strip().lower() == lower_name:
            return artist["id"]
    # no exact match in top 10 → skip
    return None

def search_artist_fuzzy(name: str):
    """
    Fuzzy-match fallback (only call this if you really want to guess).
    """
    token = get_token()
    resp = requests.get(
        SEARCH_URL,
        headers={"Authorization": f"Bearer {token}"},
        params={"q": name, "type": "artist", "limit": 1},
        timeout=5,
    )
    resp.raise_for_status()
    items = resp.json().get("artists", {}).get("items", [])
    return items[0]["id"] if items else None
