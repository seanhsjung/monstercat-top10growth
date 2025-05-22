#!/usr/bin/env python3
import os
import time
import logging
import json
import requests

# ─── Config & Logging ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

# ─── Env Vars ─────────────────────────────────────────────────────────────────
SPOTIPY_CLIENT_ID     = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
    logger.error("Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET env vars.")
    exit(1)

# ─── Token Management ───────────────────────────────────────────────────────────
TOKEN_URL = 'https://accounts.spotify.com/api/token'
_token = None
_token_expires_at = 0

def get_token():
    global _token, _token_expires_at
    if _token and time.time() < _token_expires_at:
        return _token

    resp = requests.post(
        TOKEN_URL,
        data={'grant_type': 'client_credentials'},
        auth=(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET),
        timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    _token = data['access_token']
    _token_expires_at = time.time() + data.get('expires_in', 3600) - 60
    return _token

# ─── Spotify Endpoints ─────────────────────────────────────────────────────────
SEARCH_URL       = 'https://api.spotify.com/v1/search'
ARTIST_ALBUMS    = 'https://api.spotify.com/v1/artists/{id}/albums'
BATCH_ALBUMS     = 'https://api.spotify.com/v1/albums'

# ─── Simple on-disk cache ───────────────────────────────────────────────────────
CACHE_DIR = os.path.expanduser("~/.spotify_helper_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_path(key: str) -> str:
    return os.path.join(CACHE_DIR, f"{key}.json")

def _load_cache(key: str):
    path = _cache_path(key)
    if os.path.isfile(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

def _save_cache(key: str, data):
    with open(_cache_path(key), 'w') as f:
        json.dump(data, f)

# ─── HTTP GET with rate-limit retry ─────────────────────────────────────────────
def spotify_get(url, headers, params=None, timeout=5):
    while True:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        if resp.status_code == 429:
            retry = int(resp.headers.get('Retry-After', '1'))
            logger.warning(f"Rate limited: sleeping {retry}s…")
            time.sleep(retry)
            continue
        resp.raise_for_status()
        return resp

# ─── Exact-match search + Monstercat-label check ───────────────────────────────
def search_artist_exact(name: str) -> str | None:
    token   = get_token()
    headers = {'Authorization': f"Bearer {token}"}
    params  = {'q': f'artist:"{name}"', 'type': 'artist', 'limit': 1, 'market': 'US'}

    try:
        resp = spotify_get(SEARCH_URL, headers, params)
    except requests.HTTPError as e:
        logger.warning(f"Exact search HTTP error for '{name}': {e}")
        return None

    items = resp.json().get('artists', {}).get('items', [])
    if not items:
        logger.info(f"No exact match for '{name}'")
        return None

    artist_id = items[0]['id']
    if has_monstercat_release(artist_id):
        return artist_id

    logger.info(f"'{name}' found but no Monstercat release → skipping")
    return None

def has_monstercat_release(artist_id: str) -> bool:
    token   = get_token()
    headers = {'Authorization': f"Bearer {token}"}

    # 1) page through artist's albums, caching the list of album IDs
    cache_key = f"artist_albums_{artist_id}"
    all_album_ids = _load_cache(cache_key)
    if all_album_ids is None:
        all_album_ids = []
        url    = ARTIST_ALBUMS.format(id=artist_id)
        params = {'include_groups': 'album,single', 'limit': 50, 'market': 'US'}

        while url:
            resp = spotify_get(url, headers, params)
            data = resp.json()
            all_album_ids += [a['id'] for a in data.get('items', [])]
            url = data.get('next')  # full URL for next page
            params = None

        _save_cache(cache_key, all_album_ids)

    # 2) fetch album details in batches of 20, caching each batch
    for i in range(0, len(all_album_ids), 20):
        batch = all_album_ids[i:i+20]
        batch_key = f"albums_{artist_id}_{i//20}"
        albums = _load_cache(batch_key)
        if albums is None:
            url = f"{BATCH_ALBUMS}?ids={','.join(batch)}"
            resp = spotify_get(url, headers)
            albums = resp.json().get('albums', [])
            _save_cache(batch_key, albums)

        for alb in albums:
            label = (alb.get('label') or "").lower()
            if 'monstercat' in label:
                return True

    return False
