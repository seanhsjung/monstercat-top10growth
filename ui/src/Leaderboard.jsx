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
  const [viewMode, setViewMode]   = useState("all");        // "all" | "discovery"
  const [sortMode, setSortMode]   = useState("followers");   // "followers" | "popularity"
  const [growthMode, setGrowthMode] = useState("absolute"); // "absolute" | "percent"
  const [leaders, setLeaders]     = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [selected, setSelected]   = useState(null);

  function loadData() {
    setLoading(true);
    setError(null);

    let fetcher;
    if (viewMode === "discovery") {
      fetcher = fetchTopGrowth(period, limit, "percent", "discovery");
    } else if (sortMode === "popularity") {
      fetcher = fetchTopPopularityGrowth(period, limit);
    } else {
      fetcher = fetchTopGrowth(period, limit, growthMode, "all");
    }

    return fetcher
      .then(data => {
        const normalized = (sortMode === "popularity" && viewMode === "all")
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

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, limit, viewMode, sortMode, growthMode]);

  useEffect(() => {
    if (!refreshInterval) return;
    const intervalId = setInterval(loadData, refreshInterval);
    return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, limit, viewMode, sortMode, growthMode, refreshInterval]);

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

  const isDiscovery  = viewMode === "discovery";
  const isPopularity = !isDiscovery && sortMode === "popularity";
  const isPercent    = !isDiscovery && !isPopularity && growthMode === "percent";

  const followerColLabel = isPopularity ? "Score" : "Followers";
  const deltaColLabel    = isPopularity ? "Popularity Δ"
    : isPercent || isDiscovery ? "Δ %"
    : "Δ Followers";

  function formatFollowers(val) {
    if (val == null) return "—";
    return isPopularity ? String(val) : val.toLocaleString();
  }

  function formatDelta(delta, percentDelta) {
    if (isPopularity) {
      return delta > 0 ? `+${delta}` : String(delta);
    }
    if (isPercent || isDiscovery) {
      return percentDelta == null ? "—"
        : `${percentDelta > 0 ? "+" : ""}${Number(percentDelta).toFixed(1)}%`;
    }
    return delta == null ? "—" : delta.toLocaleString();
  }

  const headingLabel = isDiscovery ? "Discovery"
    : isPopularity ? "Popularity"
    : "Growth";

  return (
    <div className={styles.container}>

      {/* Top-level: All Artists | Discovery */}
      <div className={styles.toggleRow}>
        <button
          className={`${styles.toggleBtn} ${!isDiscovery ? styles.toggleBtnActive : ""}`}
          onClick={() => setViewMode("all")}
        >
          All Artists
        </button>
        <button
          className={`${styles.toggleBtn} ${isDiscovery ? styles.toggleBtnActive : ""}`}
          onClick={() => setViewMode("discovery")}
        >
          Discovery
        </button>
      </div>

      {/* Sort sub-options — hidden in Discovery mode */}
      {!isDiscovery && (
        <>
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
        </>
      )}

      <h2 className={styles.heading}>
        Top {limit} {headingLabel} ({periodLabel})
        {isDiscovery && (
          <span className={styles.discoveryHint}> · 5k–250k followers</span>
        )}
      </h2>

      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th}>Artist</th>
            <th className={styles.th} style={{ textAlign: "right" }}>{followerColLabel}</th>
            <th className={styles.th} style={{ textAlign: "right" }}>{deltaColLabel}</th>
          </tr>
        </thead>
        <tbody>
          {leaders.map(({ id, name, delta, percentDelta, latestValue }) => (
            <tr
              key={id}
              onClick={() => setSelected(id)}
              className={styles.row}
            >
              <td className={styles.td}>{name}</td>
              <td className={styles.td} style={{ textAlign: "right" }}>
                {formatFollowers(latestValue)}
              </td>
              <td className={styles.td} style={{ textAlign: "right" }}>
                <span style={{ color: "var(--color-accent-cyan)" }}>Δ</span>{" "}
                {formatDelta(delta, percentDelta)}
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
