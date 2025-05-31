// src/api.js

// Reads from your Render‐provided env var or falls back to localhost for dev
const API = process.env.REACT_APP_API_URL || "http://localhost:8000";

/**
 * List all artists
 */
export function fetchArtists() {
  return fetch(`${API}/artists`).then((r) => r.json());
}

/**
 * Get follower metrics for one artist over a given period.
 *
 * @param {string} aid
 * @param {string} period  e.g. "24 hours", "7 days", "all"
 */
export function fetchLatest(aid, period = "24 hours") {
  const params = new URLSearchParams({ period });
  return fetch(`${API}/artist/${aid}/metrics?${params}`).then((r) => r.json());
}

/**
 * Get top‐growth leaderboard
 */
export function fetchTopGrowth(period = "7 days", limit = 10) {
  const params = new URLSearchParams({ period, limit });
  return fetch(`${API}/artists/top-growth?${params}`).then((r) => r.json());
}
