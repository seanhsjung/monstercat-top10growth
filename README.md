monstercat-top10growth

A non-commercial A&R-style leaderboard demo showcasing Monstercat artists’ fastest follower growth, powered by Monstercat’s public API and Spotify metrics, deployed on Render.

🚀 Quickstart

Clone & enter

git clone https://github.com/seanhsjung/monstercat-top10growth.git
cd monstercat-top10growth

Configure RenderRender will detect render.yaml in the root and provision:

A Postgres database (DATABASE_URL)

A scheduled ETL worker

A FastAPI web service

A static React UI

Set environment variables (locally & in Render)

export DATABASE_URL=postgresql://<user>:<pass>@<host>:5432/<db>
export SPOTIFY_CLIENT_ID=<your Spotify Client ID>
export SPOTIFY_CLIENT_SECRET=<your Spotify Client Secret>
export RATE_LIMIT_QPS=1

Seed & run locally

# Activate Python venv and install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Pull artists and map to Spotify IDs
python seed.py
python map_spotify.py

# Run one ETL pass to populate metrics
python etl.py

# Launch API
uvicorn api:app --reload

# In a new terminal, start the React UI
cd ui
npm install
npm start

Deploy on Render

git add .
git commit -m "Ready for mc-top10growth demo"
git push

Render will automatically build, deploy, and schedule your worker.

📡 API Endpoints

GET /artistsList all Monstercat artists (id, name).

GET /artists/top-growth?limit=10&period_days=7Top N artists by Spotify follower growth over the past period (in days).

GET /artist/{id}/latestLast 24 h of followers & popularity for an artist.

GET /artist/{id}/allFull historical metrics since ETL inception.

WS  /ws/{id}Pushes the latest 24 h of metrics every minute.

⚙️ Architecture & Data

ETL Worker

Hourly (or per-minute) fetch of Spotify followers & popularity

Stores each snapshot in a Postgres metrics table

API (FastAPI)

Serves artist list, raw metrics, and the top-growth leaderboard

Uses an on-the-fly CTE query to compute growth deltas

UI (React + Recharts)

Renders an A&R-style Top 10 Growth leaderboard

Proxy configured (proxy: "http://127.0.0.1:8000") for local development

Render Deployment

render.yaml declaratively defines the DB, worker, web service, and static site

Automatic deploy on every git push

⚠️ Disclaimer

Uses only public GET endpoints (no audio content)

Rate-limited to 1 request/sec

Data courtesy of Monstercat & Spotify; not affiliated

Happy scouting! 🚀

