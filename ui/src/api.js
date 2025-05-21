// ui/src/api.js

// Reads from your Render‐provided env var or falls back to localhost for dev
const API = process.env.REACT_APP_API_URL || "http://localhost:8000";

/**
 * List all artists
 */
export function fetchArtists() {
  return fetch(`${API}/artists`).then((r) => r.json());
}

/**
 * Get latest 24h metrics for one artist
 */
export function fetchLatest(aid) {
  return fetch(`${API}/artist/${aid}/latest`).then((r) => r.json());
}

/**
 * Get top‐growth leaderboard
 */
export function fetchTopGrowth(period = "7 days", limit = 10) {
  const params = new URLSearchParams({ period, limit });
  return fetch(`${API}/artists/top-growth?${params}`).then((r) => r.json());
}