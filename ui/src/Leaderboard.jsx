// ui/src/Leaderboard.jsx
import React, { useEffect, useState } from "react";
import axios from "axios";

export default function Leaderboard({ period = "7 days", limit = 10 }) {
  const [leaders, setLeaders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    axios
      .get(`/artists/top-growth?period=${encodeURIComponent(period)}&limit=${limit}`)
      .then((res) => {
        setLeaders(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Leaderboard load error:", err);
        setError(err);
        setLoading(false);
      });
  }, [period, limit]);

  if (loading) return <p>Loading leaderboard…</p>;
  if (error)  return <p style={{ color: "red" }}>Error loading leaderboard.</p>;

  return (
    <div style={{ maxWidth: 600, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h2>Top {limit} Growth (last {period})</h2>
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
              style={{
                background: i % 2 ? "#f9f9f9" : "#fff",
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
    </div>
  );
}
