import React from "react";
import Leaderboard from "./Leaderboard";

export default function App() {
  return (
    <div style={{ padding: 20, fontFamily: "sans-serif" }}>
      <h1>Monstercat A&R Demo: Top 10 Growth</h1>
      <Leaderboard period="7 days" limit={10} />
    </div>
  );
}
