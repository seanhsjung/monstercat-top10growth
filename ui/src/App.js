// ui/src/App.js
import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer
} from "recharts";

export default function App() {
  const [artists, setArtists] = useState([]);
  const [selected, setSelected] = useState("");
  const [data, setData] = useState([]);

  useEffect(() => {
    axios.get("/artists").then(res => setArtists(res.data));
  }, []);

  useEffect(() => {
    if (!selected) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://127.0.0.1:8000/ws/${selected}`);
    ws.onmessage = e => setData(JSON.parse(e.data));
    return () => ws.close();
  }, [selected]);

  return (
    <div style={{ padding: 20 }}>
      <h1>Monstercat Live Artist Pulse</h1>
      <select
        value={selected}
        onChange={e => { setData([]); setSelected(e.target.value); }}
      >
        <option value="">— Select an artist —</option>
        {artists.map(a =>
          <option key={a.id} value={a.id}>{a.name}</option>
        )}
      </select>
      {data.length > 0 && (
        <div style={{ width: "100%", height: 300, marginTop: 20 }}>
          <ResponsiveContainer>
            <LineChart data={data}>
              <XAxis dataKey="ts" tickFormatter={ts =>
                new Date(ts).toLocaleTimeString()} />
              <YAxis />
              <Tooltip labelFormatter={ts =>
                new Date(ts).toLocaleString()} />
              <Line type="monotone" dataKey="val" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
