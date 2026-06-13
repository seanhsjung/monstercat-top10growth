import React from "react";
import styles from "./KpiCard.module.css";

export default function KpiCard({ label, latestValue, absoluteDelta, percentDelta }) {
  // baselineValue is accepted by callers (preserved in toKpiProps) for future
  // use but intentionally not destructured/rendered here yet.
  const formattedValue = latestValue == null ? "—" : latestValue.toLocaleString();
  const formattedAbsolute = absoluteDelta == null ? "—"
    : `${absoluteDelta > 0 ? "+" : ""}${absoluteDelta.toLocaleString()}`;
  const formattedPercent = percentDelta == null ? "—"
    : `${percentDelta > 0 ? "+" : ""}${percentDelta.toFixed(1)}%`;

  return (
    <div className={styles.card}>
      <div className={styles.label}>{label}</div>
      <div className={styles.row}>
        <span className={styles.rowLabel}>Current</span>
        <span className={styles.rowValue}>{formattedValue}</span>
      </div>
      <div className={styles.row}>
        <span className={styles.rowLabel}>Change</span>
        <span className={styles.rowValue}>{formattedAbsolute}</span>
      </div>
      <div className={styles.row}>
        <span className={styles.rowLabel}>Growth %</span>
        <span className={styles.rowValue}>{formattedPercent}</span>
      </div>
    </div>
  );
}
