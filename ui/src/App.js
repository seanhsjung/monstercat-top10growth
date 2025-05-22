// src/App.js
import React, { useState } from "react";
import styles from "./App.module.css";
import Leaderboard from "./Leaderboard";

export default function App() {
  const windows = [
    { label: "Last 24 hours", value: "24 hours" },
    { label: "Last 3 days",   value: "3 days"    },
    { label: "Last week",      value: "7 days"    },
    { label: "Last month",     value: "30 days"   },
    { label: "All time",       value: "all"       },
  ];
  const [windowSel, setWindowSel] = useState(windows[0]);

  return (
    <div className={styles.root}>
      <h1 className={styles.title}>
        Monstercat A&R Demo: Top 10 Growth
      </h1>

      <div className={styles.selectWrapper}>
        <label>
          View window:&nbsp;
          <select
            value={windowSel.value}
            onChange={e =>
              setWindowSel(windows.find(w => w.value === e.target.value))
            }
            className={styles.select}
          >
            {windows.map(w => (
              <option key={w.value} value={w.value}>
                {w.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <Leaderboard
        period={windowSel.value}
        periodLabel={windowSel.label}
        limit={10}
        refreshInterval={5 * 60 * 1000}
      />
    </div>
  );
}
