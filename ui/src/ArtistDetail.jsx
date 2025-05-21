// ui/src/ArtistDetail.jsx
import React, { useEffect, useState } from "react";
import { fetchArtists, fetchLatest } from "./api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from "recharts";

export default function ArtistDetail({ artistId, onClose }) {
  const [data, setData]       = useState([]);
  const [name, setName]       = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchArtists(),
      fetchLatest(artistId)
    ]).then(([allArtists, metrics]) => {
      const art = allArtists.find((a) => a.id === artistId);
      setName(art?.name || artistId);

      // only followers series
      const series = metrics
        .filter((d) => d.metric === "followers")
        .map((d) => ({
          time: new Date(d.ts).toLocaleTimeString(),
          followers: d.val
        }));
      setData(series);
      setLoading(false);
    });
  }, [artistId]);

  if (loading) return <p>Loading detail…</p>;

  return (
    <div
      style={{
        marginTop: 20,
        position: "relative",
        padding: 20,
        border: "1px solid #ccc",
        borderRadius: 8,
        background: "#fff"
      }}
    >
      <button
        onClick={onClose}
        style={{
          position: "absolute",
          top: 8,
          right: 8,
          cursor: "pointer",
          border: "none",
          background: "transparent",
          fontSize: 18
        }}
      >
        ✕
      </button>
      <h3>{name} — Last 24 h Followers</h3>
      {data.length === 0 ? (
        <p>No data available yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <XAxis dataKey="time" />
            <YAxis domain={["auto", "auto"]} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="followers"
              stroke="#8884d8"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
