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
  const [leaders, setLeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [selected, setSelected] = useState(null);

  function loadData() {
    setLoading(true);
    setError(null);
    const fetcher = sortMode === "popularity" ? fetchTopPopularityGrowth : fetchTopGrowth;
    return fetcher(period, limit)
      .then(data => {
        setLeaders(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Leaderboard load error:", err);
        setError(err);
        setLoading(false);
      });
  }

  // Fetch on mount and whenever `period`, `limit`, or `sortMode` changes
  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, limit, sortMode]);

  // Poll every `refreshInterval` milliseconds
  useEffect(() => {
    if (!refreshInterval) return;
    const intervalId = setInterval(loadData, refreshInterval);
    return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, limit, sortMode, refreshInterval]);

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

      <h2 className={styles.heading}>
        Top {limit} {isPopularity ? "Popularity" : "Growth"} ({periodLabel})
      </h2>

      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th}>Artist</th>
            <th className={styles.th} style={{ textAlign: "right" }}>
              {isPopularity ? "Popularity Δ" : "Δ Followers"}
            </th>
          </tr>
        </thead>
        <tbody>
          {leaders.map(({ id, name, delta }) => (
            <tr
              key={id}
              onClick={() => setSelected(id)}
              className={styles.row}
            >
              <td className={styles.td}>{name}</td>
              <td className={styles.td} style={{ textAlign: "right" }}>
                <span style={{ color: "var(--color-accent-cyan)" }}>Δ</span>{" "}
                {isPopularity ? (delta > 0 ? `+${delta}` : delta) : delta.toLocaleString()}
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
