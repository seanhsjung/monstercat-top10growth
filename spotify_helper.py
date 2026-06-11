#!/usr/bin/env python3
import os
import re
import time
import json
import logging
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

# ─── Cache Directory ────────────────────────────────────────────────────────────
CACHE_DIR = os.path.expanduser("~/.spotify_helper_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ─── Name→ID Cache ─────────────────────────────────────────────────────────────
NAME_CACHE_FILE = os.path.join(CACHE_DIR, "matched_artists.json")
try:
    with open(NAME_CACHE_FILE, "r") as f:
        _name_cache = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    _name_cache = {}

# ─── Token Management ───────────────────────────────────────────────────────────
TOKEN_URL         = 'https://accounts.spotify.com/api/token'
_token            = None
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
ALBUM_DETAIL_URL = 'https://api.spotify.com/v1/albums/{id}'

# ─── Monstercat Endpoints ───────────────────────────────────────────────────────
MONSTERCAT_ARTISTS_API = 'https://player.monstercat.app/api/artists'
SPOTIFY_ID_RE          = re.compile(r"^[A-Za-z0-9]{22}$")

def spotify_get(url, headers, params=None, timeout=5):
    """
    Wrap requests.get with auto-retry on 429.
    """
    while True:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', '1'))
            logger.warning(f"Rate limited; sleeping {retry_after}s…")
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
        return resp

def _extract_spotify_id(url: str) -> str | None:
    """
    Given a Monstercat profile 'Links' URL, extract a 22-char Spotify
    artist ID if the URL is a recognizable open.spotify.com/artist/<id>
    link. Returns None for malformed/non-artist links.
    """
    url = (url or "").strip()
    m = re.search(r"open\.spotify\.com/artist/([^/?\s]+)", url)
    if not m:
        return None
    candidate = m.group(1).strip()
    return candidate if SPOTIFY_ID_RE.match(candidate) else None


def fetch_monstercat_spotify_links() -> dict[str, str]:
    """
    Paginate Monstercat's public /api/artists endpoint (no auth) and return
    a dict mapping {monstercat_artist_id: spotify_artist_id} for every
    artist whose 'Links' array contains a valid Spotify artist URL.
    """
    result = {}
    offset = 0
    limit  = 100

    while True:
        resp = requests.get(
            MONSTERCAT_ARTISTS_API,
            params={"limit": limit, "offset": offset},
            timeout=10,
        )
        resp.raise_for_status()
        data  = resp.json()["Artists"]
        batch = data["Data"]
        if not batch:
            break

        for artist in batch:
            for link in artist.get("Links") or []:
                if link.get("Platform") == "Spotify":
                    sid = _extract_spotify_id(link.get("Url", ""))
                    if sid:
                        result[artist["Id"]] = sid
                    break

        offset += limit
        if offset >= data["Total"]:
            break
        time.sleep(0.2)

    return result


def search_artist_exact(name: str) -> str | None:
    """
    Exact-match search, but only returns if they have a Monstercat release.
    Caches positive matches by artist name to avoid re-checking.
    """
    # 0) name-cache short circuit
    if name in _name_cache:
        return _name_cache[name]

    token   = get_token()
    headers = {'Authorization': f"Bearer {token}"}
    params  = {
        'q':        f'artist:"{name}"',
        'type':     'artist',
        'limit':    5,
        'market':   'US',
    }

    try:
        resp = spotify_get(SEARCH_URL, headers, params)
    except requests.HTTPError as e:
        logger.warning(f"Exact search HTTP error for '{name}': {e}")
        return None

    items = resp.json().get('artists', {}).get('items', [])
    if not items:
        logger.info(f"No exact match for '{name}'")
        return None

    for item in items:
        artist_id = item['id']
        if has_monstercat_release(artist_id):
            # cache and persist
            _name_cache[name] = artist_id
            with open(NAME_CACHE_FILE, "w") as f:
                json.dump(_name_cache, f, indent=2)
            return artist_id

    logger.info(f"'{name}' found ({len(items)} candidates) but none have a Monstercat release → skipping")
    return None

def has_monstercat_release(artist_id: str) -> bool:
    """
    Walks an artist's albums/singles pages; returns True once
    it finds any release whose 'label' field contains 'Monstercat'.
    """
    token   = get_token()
    headers = {'Authorization': f"Bearer {token}"}
    params  = {
        'include_groups': 'album,single',
        'limit':          50,
        'market':         'US',
    }
    next_url = ARTIST_ALBUMS.format(id=artist_id)

    while next_url:
        try:
            resp = spotify_get(next_url, headers, params)
        except requests.HTTPError as e:
            logger.warning(f"Error fetching albums for {artist_id}: {e}")
            return False

        page = resp.json()
        for album in page.get('items', []):
            try:
                alb_resp = spotify_get(
                    ALBUM_DETAIL_URL.format(id=album['id']),
                    headers
                )
            except requests.HTTPError:
                continue

            label = alb_resp.json().get('label', '') or ''
            if 'monstercat' in label.lower():
                return True

        # Spotify returns full next-page URL
        next_url = page.get('next')
        params   = None  # only needed on first page

    return False
