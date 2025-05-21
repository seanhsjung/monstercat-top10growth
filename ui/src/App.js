// ui/src/App.js
import React, { useState } from "react";
import Leaderboard from "./Leaderboard";

export default function App() {
  const windows = [
    { label: "7 days", value: "7 days" },
    { label: "30 days", value: "30 days" },
    { label: "All time", value: "all" },
  ];
  const [period, setPeriod] = useState("7 days");

  return (
    <div style={{ padding: 20, fontFamily: "sans-serif", maxWidth: 800, margin: "0 auto" }}>
      <h1>Monstercat A&R Demo: Top 10 Growth</h1>

      <label style={{ display: "block", marginBottom: 16 }}>
        View window:{" "}
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          style={{ padding: "4px 8px", fontSize: "1rem" }}
        >
          {windows.map((w) => (
            <option key={w.value} value={w.value}>
              {w.label}
            </option>
          ))}
        </select>
      </label>

      <Leaderboard
        period={period}
        limit={10}
        refreshInterval={5 * 60 * 1000} // auto-refresh every 5 minutes
      />
    </div>
  );
}
