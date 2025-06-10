import React, { useEffect, useState } from "react";
import styles from "./ArtistDetail.module.css";
import { fetchArtists, fetchLatest } from "./api"; // fetchLatest now takes (artistId, period)
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
  period = "24 hours",
  periodLabel = "Last 24 h",
  onClose
}) {
  const [data, setData]       = useState([]);
  const [name, setName]       = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchArtists(),
      fetchLatest(artistId, period)    // ← pass period here
    ]).then(([allArtists, metrics]) => {
      const art = allArtists.find(a => a.id === artistId);
      setName(art?.name || artistId);

      const series = metrics.map(d => ({
        time: new Date(d.ts).toLocaleString(),  // full date+time formatting
        followers: d.val
      }));
      setData(series);
      setLoading(false);
    });
  }, [artistId, period]);

  if (loading) return <p>Loading detail…</p>;

  return (
    <div className={styles.card}>
      <button onClick={onClose} className={styles.closeBtn}>
        ✕
      </button>
      <h3 className={styles.title}>
        {name} — {periodLabel} Followers  {/* ← use periodLabel */}
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
