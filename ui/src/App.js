// ui/src/App.js
import React from "react"
import Leaderboard from "./Leaderboard"
import "./App.css"  // if you have any global styles

function App() {
  return (
    <main style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
      <h1>Monstercat A&R Demo: Top 10 Growth</h1>
      <Leaderboard periodDays={7} limit={10} />
    </main>
  )
}

export default App
