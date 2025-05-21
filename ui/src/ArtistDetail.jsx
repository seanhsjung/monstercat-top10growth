import React, { useEffect, useState } from "react";
import axios from "axios";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function ArtistDetail({ artistId, onClose }) {
  const [data, setData]   = useState([]);
  const [name, setName]   = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    // get artist name & latest 24h
    Promise.all([
      axios.get(`/artists`), // to find the name locally
      axios.get(`/artist/${artistId}/latest`),
    ]).then(([allRes, latestRes]) => {
      const artist = allRes.data.find(a => a.id === artistId);
      setName(artist?.name || artistId);
      // transform [{metric,val,ts}] to time-series
      const series = latestRes.data
        .filter(d => d.metric === "followers")
        .map(d => ({ time: new Date(d.ts).toLocaleTimeString(), followers: d.val }));
      setData(series);
      setLoading(false);
    });
  }, [artistId]);

  if (loading) return <p>Loading detail…</p>;

  return (
    <div style={{ marginTop: 20, position: "relative", padding: 20, border: "1px solid #ccc", borderRadius: 8 }}>
      <button 
        onClick={onClose} 
        style={{ position: "absolute", top: 8, right: 8, cursor: "pointer" }}>
        ✕
      </button>
      <h3>{name} — Last 24 h Followers</h3>
      {data.length === 0 ? (
        <p>No data available yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <XAxis dataKey="time" />
            <YAxis domain={["auto","auto"]} />
            <Tooltip />
            <Line type="monotone" dataKey="followers" stroke="#8884d8" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
