monstercat-top10growth

A non-commercial A&R-style leaderboard demo showcasing Monstercat artists’ fastest follower growth, powered by Monstercat’s public API and Spotify metrics. The backend runs on Google Cloud Run with a Postgres database on Neon, and a daily GitHub Actions workflow keeps follower/popularity metrics up to date.

🚀 Quickstart

Clone & enter

git clone https://github.com/seanhsjung/monstercat-top10growth.git
cd monstercat-top10growth

Configuration

This project uses:

- **Neon** — free serverless Postgres for the `artists`/`metrics` tables
- **Google Cloud Run** — hosts the FastAPI backend (`Dockerfile` + `.github/workflows/deploy.yml`)
- **GitHub Actions** — runs the daily ETL worker (`.github/workflows/etl.yml`) and deploys to Cloud Run on every push to `main`

Set environment variables locally (e.g. via `.envrc` + direnv):

export DATABASE_URL=postgresql://<user>:<pass>@<host>/<db>?sslmode=require
export SPOTIPY_CLIENT_ID=<your Spotify Client ID>
export SPOTIPY_CLIENT_SECRET=<your Spotify Client Secret>
export RATE_LIMIT_QPS=1
export ALLOWED_ORIGINS=http://localhost:3000,https://<your-frontend>.netlify.app

GitHub repo secrets needed (Settings → Secrets and variables → Actions):

| Secret | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | etl.yml, deploy.yml | Neon connection string — used for the daily ETL run and set as a Cloud Run env var on every deploy |
| `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET` | etl.yml | Spotify API credentials |
| `GCP_SA_KEY` | deploy.yml | Service account JSON key for deploying to Cloud Run |
| `GCP_PROJECT_ID` | deploy.yml | Target GCP project ID |

`ALLOWED_ORIGINS` is not set by default (the API falls back to `http://localhost:3000`). Once a frontend is deployed, set it via `gcloud run services update` (see below) or add it to `deploy.yml`'s `--set-env-vars`.

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

Deploy to Cloud Run

Pushing to `main` triggers `.github/workflows/deploy.yml`, which builds the Docker image via Cloud Build (using the repo's `Dockerfile`) and deploys it to Cloud Run with `--allow-unauthenticated` so the frontend can reach it.

git add .
git commit -m "Ready for mc-top10growth demo"
git push

One-time GCP setup (before the first push):

1. Create or select a GCP project and note its Project ID.
2. Enable the required APIs:
   ```
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project=<PROJECT_ID>
   ```
3. Create a deploy service account and grant it the roles it needs:
   ```
   gcloud iam service-accounts create gh-deployer --display-name="GitHub Actions Cloud Run deployer" --project=<PROJECT_ID>
   ```
   Roles: `roles/run.admin`, `roles/cloudbuild.builds.editor`, `roles/iam.serviceAccountUser`, `roles/storage.admin`, `roles/artifactregistry.admin`

   (`storage.admin` is needed for `gcloud run deploy --source` to create its source-upload bucket; `artifactregistry.admin` is needed for it to create the `cloud-run-source-deploy` repo on first deploy.)
4. Generate a JSON key and add it as the `GCP_SA_KEY` GitHub secret (and `GCP_PROJECT_ID` as another secret). Delete the local key file afterward.

`deploy.yml` passes `DATABASE_URL` to Cloud Run via `--set-env-vars` on every deploy, so no manual post-deploy step is needed for the API to start. If you later deploy a frontend, set `ALLOWED_ORIGINS` the same way (either add it to `deploy.yml`'s `flags`, or run `gcloud run services update mc-top10growth-api --region=us-central1 --update-env-vars ALLOWED_ORIGINS="https://<your-frontend>.netlify.app" --project=<PROJECT_ID>`).

Deploy the Frontend to Netlify

The React app lives in `ui/` and talks to the Cloud Run API via `fetch` calls in `ui/src/api.js`, which read `process.env.REACT_APP_API_URL` (baked in at build time). `ui/.env.production` already sets this to the live Cloud Run URL, so no Netlify environment variable is required — though you can override it by setting `REACT_APP_API_URL` in the Netlify UI if the API URL ever changes (Netlify's build env vars take precedence over `.env.production`).

`ui/public/_redirects` (`/*  /index.html  200`) already handles SPA routing, so no changes were needed there. A root-level `netlify.toml` was added because the app lives in a subdirectory — it tells Netlify the base directory, build command, and publish directory:

```toml
[build]
  base = "ui"
  command = "npm run build"
  publish = "build"
```

Connect the repo to Netlify:

1. In the Netlify dashboard: **Add new site → Import an existing project → Deploy with GitHub** (authorize access to `seanhsjung/monstercat-top10growth` if prompted).
2. Netlify auto-detects `netlify.toml` and pre-fills Base directory `ui`, Build command `npm run build`, Publish directory `ui/build`. Leave these as-is.
3. Click **Deploy site**. Netlify installs dependencies, runs the build, and publishes `ui/build` to a generated URL like `https://<random-name>.netlify.app`.
4. (Optional) Rename the site under **Site configuration → General → Site details → Change site name** for a friendlier URL.
5. Add the Netlify URL to the API's CORS allow-list via `deploy.yml`'s `flags` (already done for `https://monstercat-top10growth.netlify.app` — update this if you rename the site or add another frontend URL):
   ```
   flags: --allow-unauthenticated --set-env-vars=DATABASE_URL=${{ secrets.DATABASE_URL }},ALLOWED_ORIGINS=https://<your-site>.netlify.app
   ```
   then push to `main` to redeploy the API with the updated CORS origin.

Future pushes to `main` that touch `ui/` will trigger a Netlify rebuild automatically once the site is connected.

📡 API Endpoints

GET /artists — List all Monstercat artists (id, name).

GET /artists/top-growth?period=7 days&limit=10 — Top N artists by Spotify follower growth over the given period (`24 hours`, `3 days`, `7 days`, `30 days`, or `all`).

GET /artist/{id}/latest — Last 24 h of followers & popularity for an artist.

GET /artist/{id}/metrics?period=7 days — Follower history for an artist over a given period.

WS  /ws/{id} — Pushes the latest 24 h of metrics every minute.

⚙️ Architecture & Data

ETL Worker

Daily fetch (GitHub Actions cron, `.github/workflows/etl.yml`) of Spotify followers & popularity for every mapped artist

Stores each day's snapshot as new rows in the Postgres `metrics` table — growth is computed from the spread between snapshots, so historical rows are never overwritten

API (FastAPI)

Serves artist list, raw metrics, and the top-growth leaderboard

Uses an on-the-fly CTE query to compute growth deltas

UI (React + Recharts)

Renders an A&R-style Top 10 Growth leaderboard

Proxy configured (proxy: "http://127.0.0.1:8000") for local development

Cloud Run Deployment

`Dockerfile` builds the FastAPI image; `.github/workflows/deploy.yml` deploys it to Cloud Run on every push to `main` via Cloud Build (no manual image push needed)

`.github/workflows/etl.yml` runs independently on a daily cron — there's no long-running worker process to host

Spotify Matching (`map_spotify.py`)

Each Monstercat artist's `spotify_id` is resolved via three tiers, in priority order:

1. **Manual override** — `manual_mappings.json`, for hand-verified edge cases
2. **Monstercat profile link** — Monstercat's own `/api/artists` response includes a `Links` array; if it contains a valid `open.spotify.com/artist/<id>` URL, that ID is used directly (covers the vast majority of artists, with no Spotify API calls)
3. **Spotify search fallback** — for any artist with neither, search Spotify by exact name (checking up to 5 candidates) and verify a Monstercat-labeled release before accepting a match

Any artist that still can't be resolved is written to `skipped_artists.csv` for manual review.

⚠️ Disclaimer

Uses only public GET endpoints (no audio content)

Rate-limited to 1 request/sec

Data courtesy of Monstercat & Spotify; not affiliated

Happy scouting! 🚀
