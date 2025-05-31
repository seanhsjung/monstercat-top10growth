// src/ArtistDetail.jsx
import React, { useEffect, useState } from "react";
import styles from "./ArtistDetail.module.css";
import { fetchArtists, fetchLatest } from "./api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from "recharts";

export default function ArtistDetail({
  artistId,
  period = "24 hours",         // default fallback
  periodLabel = "Last 24 h",   // default fallback
  onClose
}) {
  const [data, setData]       = useState([]);
  const [name, setName]       = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);

    // 1) Fetch all artists (to look up the name)
    // 2) Fetch follower‐over‐time for this artist & period
    Promise.all([fetchArtists(), fetchLatest(artistId, period)]).then(
      ([allArtists, metrics]) => {
        const art = allArtists.find(a => a.id === artistId);
        setName(art?.name || artistId);

        // Build a data series: one point per timestamp
        const series = metrics.map(d => ({
          // use locale string to show date+time (because range might be >24h)
          time: new Date(d.ts).toLocaleString(),
          followers: d.val
        }));

        setData(series);
        setLoading(false);
      }
    );
  }, [artistId, period]);

  if (loading) return <p>Loading detail…</p>;

  return (
    <div className={styles.card}>
      <button onClick={onClose} className={styles.closeBtn}>
        ✕
      </button>
      <h3 className={styles.title}>
        {name} — {periodLabel} Followers
      </h3>

      {data.length === 0 ? (
        <p>No data available for this period.</p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <XAxis dataKey="time" stroke="var(--color-text-sub)" />
            <YAxis domain={["auto","auto"]} stroke="var(--color-text-sub)" />
            <Tooltip
              wrapperStyle={{
                backgroundColor: "rgba(26,26,26,0.9)",
                border: "none",
                color: "var(--color-text-main)"
              }}
            />
            <Line
              type="monotone"
              dataKey="followers"
              stroke="var(--color-accent-cyan)"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
