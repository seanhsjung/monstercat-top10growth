# monstercat-live-pulse
cat > README.md << 'EOF'
# Monstercat Live Artist Pulse

A non-commercial demo using only Monstercat’s open GET API endpoints,
augmented with Spotify stats, deployed via Render.

## 🚀 Quickstart
1. Clone & `cd monstercat-live-pulse`  
2. Provision with `render.yaml`  
3. Set env vars: `SPOTIFY_TOKEN`, `RATE_LIMIT_QPS=1`  
4. Deploy & run seed scripts; UI auto-updates thereafter.

## ⚠️ Disclaimer
- Only public GET endpoints (no audio)  
- Rate limit: 1 req/s  
- Data courtesy of Monstercat’s public API; not affiliated  
EOF
