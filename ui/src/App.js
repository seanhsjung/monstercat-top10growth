// ui/src/App.js
import React, { useState } from "react";
import Leaderboard from "./Leaderboard";

export default function App() {
  const windows = [
    { label: "Last 24 hours", value: "24 hours" },
    { label: "Last 3 days",   value: "3 days" },
    { label: "Last week",      value: "7 days" },
    { label: "Last month",     value: "30 days" },
    { label: "All time",       value: "all" },
  ];

  // track the selected window object
  const [windowSel, setWindowSel] = useState(windows[0]);

  return (
    <div style={{ padding: 20, fontFamily: "sans-serif", maxWidth: 800, margin: "0 auto" }}>
      <h1>Monstercat A&R Demo: Top 10 Growth</h1>

      <label style={{ display: "block", marginBottom: 16 }}>
        View window:{" "}
        <select
          value={windowSel.value}
          onChange={(e) =>
            setWindowSel(windows.find((w) => w.value === e.target.value))
          }
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
        period={windowSel.value}      // for the API query
        periodLabel={windowSel.label} // for the heading
        limit={10}
        refreshInterval={5 * 60 * 1000}
      />
    </div>
  );
}
