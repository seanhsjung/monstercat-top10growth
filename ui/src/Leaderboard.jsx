// ui/src/Leaderboard.jsx
import React, { useEffect, useState } from "react";
import { fetchTopGrowth } from "./api";
import ArtistDetail from "./ArtistDetail";

export default function Leaderboard({
  period,
  periodLabel,
  limit = 10,
  refreshInterval,
}) {
  const [leaders, setLeaders]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const [selected, setSelected] = useState(null);

  const fetchData = () => {
    setLoading(true);
    setError(null);
    fetchTopGrowth(period, limit)
      .then((data) => {
        setLeaders(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Leaderboard load error:", err);
        setError(err);
        setLoading(false);
      });
  };

  // initial load & on period/limit change
  useEffect(fetchData, [period, limit]);

  // polling
  useEffect(() => {
    if (!refreshInterval) return;
    const iv = setInterval(fetchData, refreshInterval);
    return () => clearInterval(iv);
  }, [period, limit, refreshInterval]);

  if (loading) return <p>Loading leaderboard…</p>;
  if (error)   return <p style={{ color: "red" }}>Error loading leaderboard.</p>;

  return (
    <div style={{ maxWidth: 600, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h2>
        Top {limit} Growth ({periodLabel})
      </h2>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid #ddd" }}>
            <th style={{ textAlign: "left", padding: "8px" }}>Artist</th>
            <th style={{ textAlign: "right", padding: "8px" }}>Δ Followers</th>
          </tr>
        </thead>
        <tbody>
          {leaders.map(({ id, name, delta }, i) => (
            <tr
              key={id}
              onClick={() => setSelected(id)}
              style={{
                background: i % 2 ? "#f9f9f9" : "#fff",
                cursor: "pointer",
              }}
            >
              <td style={{ padding: "8px" }}>{name}</td>
              <td style={{ padding: "8px", textAlign: "right" }}>
                {delta.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {selected && (
        <ArtistDetail artistId={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
