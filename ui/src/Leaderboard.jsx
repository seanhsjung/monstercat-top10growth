// src/Leaderboard.jsx

import React, { useEffect, useState } from "react";
import styles from "./Leaderboard.module.css";
import { fetchTopGrowth, fetchTopPopularityGrowth } from "./api";
import ArtistDetail from "./ArtistDetail";

export default function Leaderboard({
  period,
  periodLabel,
  limit = 10,
  refreshInterval,
}) {
  const [sortMode, setSortMode] = useState("followers"); // "followers" | "popularity"
  const [growthMode, setGrowthMode] = useState("absolute"); // "absolute" | "percent"
  const [leaders, setLeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [selected, setSelected] = useState(null);

  function loadData() {
    setLoading(true);
    setError(null);
    const fetcher = sortMode === "popularity"
      ? fetchTopPopularityGrowth(period, limit)
      : fetchTopGrowth(period, limit, growthMode);
    return fetcher
      .then(data => {
        const normalized = sortMode === "popularity"
          ? data.map(({ id, name, delta, earliest_popularity, latest_popularity }) => ({
              id,
              name,
              delta,
              percentDelta: null,
              latestValue: latest_popularity,
              baselineValue: earliest_popularity,
            }))
          : data.map(({ id, name, absolute_delta, percent_delta, latest_value, baseline_value }) => ({
              id,
              name,
              delta: absolute_delta,
              percentDelta: percent_delta,
              latestValue: latest_value,
              baselineValue: baseline_value,
            }));
        setLeaders(normalized);
        setLoading(false);
      })
      .catch(err => {
        console.error("Leaderboard load error:", err);
        setError(err);
        setLoading(false);
      });
  }

  // Fetch on mount and whenever `period`, `limit`, `sortMode`, or `growthMode` changes
  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, limit, sortMode, growthMode]);

  // Poll every `refreshInterval` milliseconds
  useEffect(() => {
    if (!refreshInterval) return;
    const intervalId = setInterval(loadData, refreshInterval);
    return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, limit, sortMode, growthMode, refreshInterval]);

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <img
          src="/monstercat_logo.png"
          alt="Loading leaderboard…"
          className={styles.spinner}
        />
      </div>
    );
  }

  if (error) {
    return <p style={{ color: "red" }}>Error loading leaderboard.</p>;
  }

  const isPopularity = sortMode === "popularity";

  return (
    <div className={styles.container}>
      <div className={styles.toggleRow}>
        <button
          className={`${styles.toggleBtn} ${!isPopularity ? styles.toggleBtnActive : ""}`}
          onClick={() => setSortMode("followers")}
        >
          Follower Growth
        </button>
        <button
          className={`${styles.toggleBtn} ${isPopularity ? styles.toggleBtnActive : ""}`}
          onClick={() => setSortMode("popularity")}
        >
          Rising Popularity
        </button>
      </div>

      {!isPopularity && (
        <div className={styles.toggleRow}>
          <button
            className={`${styles.toggleBtn} ${growthMode === "absolute" ? styles.toggleBtnActive : ""}`}
            onClick={() => setGrowthMode("absolute")}
          >
            Absolute Growth
          </button>
          <button
            className={`${styles.toggleBtn} ${growthMode === "percent" ? styles.toggleBtnActive : ""}`}
            onClick={() => setGrowthMode("percent")}
          >
            Relative Growth (%)
          </button>
        </div>
      )}

      <h2 className={styles.heading}>
        Top {limit} {isPopularity ? "Popularity" : "Growth"} ({periodLabel})
      </h2>

      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th}>Artist</th>
            <th className={styles.th} style={{ textAlign: "right" }}>
              {isPopularity ? "Popularity Δ" : growthMode === "percent" ? "Δ %" : "Δ Followers"}
            </th>
          </tr>
        </thead>
        <tbody>
          {leaders.map(({ id, name, delta, percentDelta }) => (
            <tr
              key={id}
              onClick={() => setSelected(id)}
              className={styles.row}
            >
              <td className={styles.td}>{name}</td>
              <td className={styles.td} style={{ textAlign: "right" }}>
                <span style={{ color: "var(--color-accent-cyan)" }}>Δ</span>{" "}
                {isPopularity
                  ? (delta > 0 ? `+${delta}` : delta)
                  : growthMode === "percent"
                    ? (percentDelta == null ? "—" : `${percentDelta > 0 ? "+" : ""}${percentDelta.toFixed(1)}%`)
                    : delta.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {selected && (
        <ArtistDetail
          artistId={selected}
          period={period}
          periodLabel={periodLabel}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
