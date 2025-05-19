import os
import time
import requests

CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

_token_info = {"access_token": None, "expires_at": 0}

def get_token():
    """
    Returns a valid Spotify bearer token, refreshing it if it’s expired.
    """
    now = int(time.time())
    # If we have a token and it won’t expire for at least another 60 seconds, reuse it
    if _token_info["access_token"] and now < _token_info["expires_at"] - 60:
        return _token_info["access_token"]

    # Otherwise, request a new one via Client Credentials flow
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
    )
    resp.raise_for_status()
    payload = resp.json()
    # Cache the new token and its expiry timestamp
    _token_info["access_token"] = payload["access_token"]
    _token_info["expires_at"]   = now + payload.get("expires_in", 3600)
    return payload["access_token"]


def search_artist(name: str) -> str | None:
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    params  = {"q": name, "type": "artist", "limit": 1}
    resp    = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)
    resp.raise_for_status()
    items = resp.json().get("artists", {}).get("items", [])
    return items[0]["id"] if items else None

def get_artist_stats(artist_id: str) -> dict:
    """
    Fetches the artist’s data (followers & popularity) from Spotify.
    """
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/artists/{artist_id}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()
