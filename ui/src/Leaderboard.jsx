import React, { useEffect, useState } from "react";
import styles from "./Leaderboard.module.css";
import { fetchTopGrowth } from "./api";
import ArtistDetail from "./ArtistDetail";

export default function Leaderboard({
  period,
  periodLabel,
  limit = 10,
  refreshInterval,
}) {
  const [leaders, setLeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [selected, setSelected] = useState(null);

  // Fetch on mount and whenever `period` or `limit` changes
  useEffect(() => {
    setLoading(true);
    setError(null);

    fetchTopGrowth(period, limit)
      .then(data => {
        setLeaders(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Leaderboard load error:", err);
        setError(err);
        setLoading(false);
      });
  }, [period, limit]);

  // Poll every `refreshInterval` milliseconds
  useEffect(() => {
    if (!refreshInterval) return;

    const intervalId = setInterval(() => {
      setLoading(true);
      setError(null);

      fetchTopGrowth(period, limit)
        .then(data => {
          setLeaders(data);
          setLoading(false);
        })
        .catch(err => {
          console.error("Leaderboard load error:", err);
          setError(err);
          setLoading(false);
        });
    }, refreshInterval);

    return () => clearInterval(intervalId);
  }, [period, limit, refreshInterval]);

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.loadingBar} />
      </div>
    );
  }

  if (error) {
    return <p style={{ color: "red" }}>Error loading leaderboard.</p>;
  }

  return (
    <div className={styles.container}>
      <h2 className={styles.heading}>
        Top {limit} Growth ({periodLabel})
      </h2>

      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th}>Artist</th>
            <th className={styles.th}>Δ Followers</th>
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
                {delta.toLocaleString()}
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
