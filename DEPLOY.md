# Deploying Reel Oracle (Render + Vercel)

Backend (FastAPI) on Render, frontend (Vite/React) on Vercel. The two reference each other, so deploy in this order.

## 1. Backend → Render

1. Push this repo to GitHub, then create a new Web Service on Render from it. `render.yaml` (repo root) already declares the service — Render will pick it up via "Blueprint" deploy, or you can create the service manually and it'll read `rootDir: backend`, the build/start commands, and `healthCheckPath`.
2. In the Render dashboard, set the env vars marked `sync: false` in `render.yaml` (Render won't accept committed secrets, so these must be set by hand):
   - `YOUTUBE_API_KEY` — from the [Google Cloud Console](https://console.cloud.google.com/apis/library/youtube.googleapis.com).
   - `DATABASE_URL` — see **Persistence**, below, before picking a value.
   - `CORS_ORIGINS` — leave a placeholder for now (e.g. `https://localhost`); you'll set the real Vercel URL in step 3.
   - `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` / `GOOGLE_OAUTH_REDIRECT_URI` — only if you want the Creator Analytics (OAuth) tab working; see **OAuth**, below.
3. Deploy. Note the resulting service URL (`https://<your-service>.onrender.com`).

## 2. Frontend → Vercel

1. Import the repo into Vercel, with **Root Directory** set to `frontend`. `vercel.json` already declares the build command, output directory, and SPA rewrite.
2. Set the env var `VITE_API_BASE_URL` to your Render URL from step 1 (Vercel dashboard → Settings → Environment Variables — `frontend/.env.example` documents the shape).
3. Deploy. Note the resulting production URL (`https://<your-project>.vercel.app`).

## 3. Close the loop

Back in Render, update `CORS_ORIGINS` to your real Vercel production URL (comma-separated if you also want a custom domain), then redeploy the backend so the new value takes effect.

**Vercel preview deployments** (every branch/PR gets its own random `*.vercel.app` subdomain) are already covered — `backend/app/main.py` allows `https://*.vercel.app` via `allow_origin_regex` in addition to the fixed `CORS_ORIGINS` list, so you don't need to add every preview URL by hand.

## Things worth deciding before a client demo

- **SQLite persistence.** `DATABASE_URL` defaults to a local SQLite file. Render's free web service filesystem is **not persistent across deploys/restarts** — tracked channels/videos, snapshot history, and any connected OAuth account will be wiped the next time the service redeploys or spins back up from idle. For a one-off demo this is harmless; if you want Tracking history to survive, either add a Render persistent disk mounted at the SQLite file's path, or point `DATABASE_URL` at a Render Postgres instance (free tier available) instead.
- **Cold starts.** Render's free plan spins a service down after ~15 minutes idle; the next request takes 30-50s to wake it. If you're sending a client a link cold (not screen-sharing), that first load will sit on the "checking connection" state for a while. Either upgrade the Render plan for the demo window, ping the service a minute before the call, or say so if you want the loader copy to acknowledge a cold start explicitly.
- **OAuth redirect URI.** `GOOGLE_OAUTH_REDIRECT_URI` defaults to `http://localhost:8010/oauth/callback`. For the Creator Analytics tab to work in production, set it to `https://<your-render-service>.onrender.com/oauth/callback` on Render, and add that exact URL to the OAuth client's **Authorized redirect URIs** in Google Cloud Console.
