// ui/src/Leaderboard.jsx
import React, { useEffect, useState } from "react";
import axios from "axios";
import ArtistDetail from "./ArtistDetail";

export default function Leaderboard({ period = "7 days", limit = 10, refreshInterval }) {
  const [leaders, setLeaders]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const [selected, setSelected] = useState(null);

  // Build the URL for fetching
  const buildUrl = () => {
    const API = process.env.REACT_APP_API_URL || "";
    const params = new URLSearchParams({
      period: period,
      limit: limit.toString(),
    }).toString();
    return `${API}/artists/top-growth?${params}`;
  };

  const fetchData = () => {
    setLoading(true);
    setError(null);
    axios
      .get(buildUrl())
      .then((res) => {
        setLeaders(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Leaderboard load error:", err);
        setError(err);
        setLoading(false);
      });
  };

  // Initial load & reload on period or limit change
  useEffect(fetchData, [period, limit]);

  // Polling
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
        Top {limit} Growth (last{" "}
        {period === "all" ? "all time" : period})
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
        <ArtistDetail
          artistId={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
