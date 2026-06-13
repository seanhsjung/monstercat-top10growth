import React, { useEffect, useState } from "react";
import styles from "./ArtistDetail.module.css";
import { fetchArtists, fetchLatest, fetchArtistGrowth } from "./api"; // fetchLatest now takes (artistId, period)
import KpiCard from "./KpiCard";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from "recharts";

// Maps the backend's {latest_value, baseline_value, absolute_delta, percent_delta}
// shape to KpiCard's prop names. baselineValue is preserved for future use
// (e.g. a "2 → 43" or "Started at 2" context line) even though KpiCard
// doesn't render it yet.
function toKpiProps(metricData) {
  if (!metricData) {
    return { latestValue: null, baselineValue: null, absoluteDelta: null, percentDelta: null };
  }
  return {
    latestValue: metricData.latest_value,
    baselineValue: metricData.baseline_value,
    absoluteDelta: metricData.absolute_delta,
    percentDelta: metricData.percent_delta,
  };
}

// Config-driven KPI cards: add a row here to surface another metric
// (e.g. Monthly Listeners) without touching the render logic below.
const KPI_METRICS = [
  { key: "followers", label: "Followers" },
  { key: "popularity", label: "Popularity" },
];

export default function ArtistDetail({
  artistId,
  period = "24 hours",
  periodLabel = "Last 24 h",
  onClose
}) {
  const [data, setData]       = useState([]);
  const [name, setName]       = useState("");
  const [growth, setGrowth]   = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchArtists(),
      fetchLatest(artistId, period),   // ← pass period here
      fetchArtistGrowth(artistId, period)
    ]).then(([allArtists, metrics, growthData]) => {
      const art = allArtists.find(a => a.id === artistId);
      setName(art?.name || artistId);

      const series = metrics.map(d => ({
        time: new Date(d.ts).toLocaleString(),  // full date+time formatting
        followers: d.val
      }));
      setData(series);
      setGrowth(growthData || {});
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
        {name} — {periodLabel}
      </h3>

      <div className={styles.kpiRow}>
        {KPI_METRICS.map(({ key, label }) => (
          <KpiCard key={key} label={label} {...toKpiProps(growth[key])} />
        ))}
      </div>

      <h4 className={styles.chartTitle}>Follower History</h4>

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
