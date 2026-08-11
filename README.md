# Reel Oracle

> A full-stack YouTube intelligence platform for discovering trends, analysing content, predicting performance, generating ideas, monitoring audience response, comparing creators, and tracking growth.

[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![YouTube API](https://img.shields.io/badge/YouTube-Data_API_v3-FF0000?logo=youtube&logoColor=white)](https://developers.google.com/youtube/v3)
[![Render](https://img.shields.io/badge/Backend-Render-46E3B7?logo=render&logoColor=black)](https://render.com/)
[![Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?logo=vercel&logoColor=white)](https://vercel.com/)

## Live Demo

- **Frontend:** `Add your Vercel URL here`
- **Backend API:** `Add your Render URL here`
- **API documentation:** `Add your Render URL here/docs`

> The free Render instance may sleep when inactive. The first request after a period of inactivity can take longer while the backend wakes up.

## Screenshots

### Landing Page

**[Add image here — Reel Oracle landing page]**

### Platform Overview

**[Add image here — Overview dashboard showing the feature directory and watchlist digest]**

### Discover

**[Add image here — Discover page showing Trend Radar, Content Gaps, and Competitor Comparison]**

### Analyse

**[Add image here — Analyse page showing Video Intelligence, sentiment, thumbnail score, and channel audit]**

### Predict

**[Add image here — Predict page showing virality prediction and channel growth forecast]**

### Create

**[Add image here — Create page showing generated titles and upload-timing analysis]**

### Monitor

**[Add image here — Monitor page showing comment sentiment and performance anomalies]**

### Recommend

**[Add image here — Recommend page showing similar videos and next-video ideas]**

### Tracking

**[Add image here — Tracking page showing tracked channels, historical data, leaderboards, and milestones]**

## About the Project

Reel Oracle is a portfolio-grade YouTube intelligence platform built using live data from the YouTube Data API v3.

It combines channel and video statistics with:

- Custom analytics
- Natural-language processing
- Sentiment analysis
- Image and thumbnail analysis
- Machine-learning experiments
- Time-series forecasting
- Creator-network analysis
- Historical channel and video tracking
- Recommendation systems

The project demonstrates full-stack development across API integration, backend architecture, database persistence, statistical analysis, machine learning, frontend design, deployment, and error handling.

Reel Oracle is currently designed as a single-operator portfolio application rather than a production multi-tenant SaaS platform.

## Main Features

The application is organized into seven intelligence modules.

### 1. Discover

The Discover section helps identify trends, competitors, content opportunities, and creator relationships.

Features include:

- Multi-topic trend scanning
- Trend burst detection
- Regional and category filters
- Video-length filters
- Competitor channel comparison
- Content-gap detection
- Upload-cadence comparison
- Creator-network visualization
- PageRank-based channel centrality
- Topic and product intelligence
- Purchase-intent detection
- Competitor mention analysis
- Upcoming-premiere discovery
- Active livestream discovery
- TF-IDF-based semantic search

### 2. Analyse

The Analyse section provides detailed intelligence about videos, playlists, thumbnails, and channels.

Features include:

- Video statistics and engagement analysis
- Comment sentiment analysis
- Emotion and toxicity scoring
- Aspect-based comment analysis
- Virality scoring
- Thumbnail quality analysis
- Misleading-title risk detection
- Suspicious engagement and bot-risk analysis
- Playlist performance summaries
- Best and weakest playlist-video detection
- Brand-safety scoring
- Complete channel portfolio audits
- Prioritized channel recommendations

### 3. Predict

The Predict section estimates future video and channel performance.

Features include:

- Heuristic virality prediction
- Random Forest virality prediction
- Seven-day projected view ranges
- Heuristic channel-growth forecasting
- ARIMA-based growth forecasting
- Feature-importance reporting
- Transparent model fallback behaviour

The trained models require sufficient historical tracking data. If there is not enough data, the application automatically falls back to heuristic analysis.

### 4. Create

The Create section assists with content planning.

Features include:

- YouTube title generation
- Educational, engaging, and news title styles
- Predicted CTR classification
- Clickbait-risk scoring
- Best upload-day analysis
- Best upload-hour analysis
- Personalized title insights
- Performance correlation using tracked videos

The title generator uses deterministic templates and scoring rules. It does not require a paid generative-AI API.

### 5. Monitor

The Monitor section provides current audience and performance signals.

Features include:

- Poll-based comment sentiment snapshots
- Multilingual comment detection
- Best-effort translation of non-English comments
- Emotion-distribution analysis
- Toxicity estimation
- Performance-anomaly detection
- Active livestream discovery
- Live-chat sentiment polling
- WebSocket-based live-chat monitoring

Live-chat features work only while a video is actively broadcasting and has live chat enabled.

### 6. Recommend

The Recommend section helps identify related content and future video opportunities.

Features include:

- Similar-video discovery
- Competitor-derived content ideas
- Content-gap-based recommendations
- Explanations for why each idea may represent an opportunity

### 7. Tracking

The Tracking section stores channel and video information over time.

Features include:

- Track and untrack channels
- Track and untrack videos
- Channel snapshot history
- Video snapshot history
- Watchlist digest
- Channel leaderboards
- Video leaderboards
- Milestone detection
- Historical channel comparison
- CSV history export
- Optional Google OAuth Creator Analytics

## Example: Analysing MrBeast

The application accepts YouTube channel IDs, video IDs, and full URLs depending on the selected field.

```text
MrBeast channel ID:
UCX6OQ3DkcsbYNE6H8uQQuVA

Example MrBeast video:
https://www.youtube.com/watch?v=IQxea9UB1nQ

MrBeast uploads playlist:
UUX6OQ3DkcsbYNE6H8uQQuVA

Dude Perfect channel ID:
UCRijo3ddMTht_IHyNSNXpNQ
```

Suggested demonstration flow:

1. Open the Tracking page.
2. Track MrBeast and Dude Perfect.
3. Open the Analyse page.
4. Paste the example MrBeast video URL.
5. Run video, thumbnail, misleading-risk, and engagement-risk analysis.
6. Open Discover and compare both channels.
7. Run content-gap analysis.
8. Generate titles for a large-scale challenge in Create.
9. Return to Overview to show the collected information.

## Application Architecture

```text
User Browser
     |
     v
React + Vite Frontend
Hosted on Vercel
     |
     | Axios REST requests
     | WebSocket connections
     v
FastAPI Backend
Hosted on Render
     |
     |-- YouTube Data API v3
     |-- Analytics services
     |-- NLP and sentiment services
     |-- Machine-learning services
     |-- Thumbnail analysis
     |-- Graph analysis
     |-- Tracking repository
     v
SQLite or PostgreSQL Database
```

## Technology Stack

### Frontend

| Technology | Purpose |
|---|---|
| React 19 | Component-based user interface |
| Vite 8 | Development server and production build |
| Axios | Backend API communication |
| Recharts | Historical and analytical charts |
| CSS | Responsive layout and visual design |

### Backend

| Technology | Purpose |
|---|---|
| Python 3.12 | Backend runtime |
| FastAPI | REST API and WebSocket endpoints |
| Uvicorn | ASGI application server |
| Pydantic Settings | Typed environment configuration |
| SQLAlchemy | Database and repository layer |
| SQLite | Default local database |
| psycopg2 | Optional PostgreSQL support |
| Requests | External HTTP requests |
| Pillow | Image processing |
| OpenCV | Thumbnail analysis |
| scikit-learn | TF-IDF, clustering, regression, and Random Forest models |
| statsmodels | ARIMA forecasting |
| NetworkX | Creator-network graphs and PageRank |
| langdetect | Local language identification |
| python-dotenv | Local environment configuration |

### External Services

| Service | Required? | Purpose |
|---|---:|---|
| YouTube Data API v3 | Yes | Public YouTube data |
| Google OAuth 2.0 | Optional | Private analytics for a connected creator account |
| MyMemory Translation API | Optional | Best-effort comment translation |
| Render | Deployment | FastAPI backend hosting |
| Vercel | Deployment | React frontend hosting |

## What Is Not Used

The project intentionally does not require:

- OpenAI API
- Gemini API
- Claude API
- A paid generative-AI service
- A hosted large language model
- Transformer-model downloads
- Redis
- Celery
- Kafka
- Docker
- Firebase authentication
- Supabase authentication
- User registration
- Multi-tenant accounts
- Fabricated analytics
- Hard-coded demonstration results

Title generation, sentiment analysis, scoring, and recommendations use deterministic templates, lexicons, statistical analysis, and local machine-learning methods.

## Repository Structure

```text
YT/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   `-- routes.py
|   |   |-- core/
|   |   |   `-- config.py
|   |   |-- db/
|   |   |-- models/
|   |   |-- repositories/
|   |   `-- services/
|   |       `-- youtube/
|   |           |-- analytics.py
|   |           |-- bot_detection.py
|   |           |-- client.py
|   |           |-- graph_analysis.py
|   |           |-- language.py
|   |           |-- ml_models.py
|   |           |-- oauth.py
|   |           |-- resources.py
|   |           |-- sentiment.py
|   |           |-- snapshot_sync.py
|   |           `-- tracking_insights.py
|   |-- .env.example
|   `-- requirements.txt
|
|-- frontend/
|   |-- public/
|   |-- src/
|   |   |-- api/
|   |   |-- components/
|   |   |-- pages/
|   |   |-- App.jsx
|   |   `-- main.jsx
|   |-- .env.example
|   |-- package.json
|   |-- vercel.json
|   `-- vite.config.js
|
|-- render.yaml
|-- DEPLOY.md
|-- DESIGN.md
|-- PRODUCT.md
|-- run-backend.cmd
`-- run-frontend.cmd
```

## Local Installation

### Prerequisites

Install:

- Git
- Python 3.12
- Node.js
- npm
- A YouTube Data API v3 key

### Clone the Repository

```bash
git clone https://github.com/eddytiya/YT.git
cd YT
```

## Backend Setup

Open a terminal in the repository:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `backend/.env` and replace:

```env
YOUTUBE_API_KEY=change_me
```

with your actual YouTube API key.

Start the backend:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Backend links:

- API: <http://localhost:8010>
- API status: <http://localhost:8010/status>
- API documentation: <http://localhost:8010/docs>

## Frontend Setup

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev -- --port 5175
```

Open:

```text
http://localhost:5175
```

During local development, the frontend uses:

```text
http://localhost:8010
```

as the default backend URL.

## Environment Variables

### Backend Variables

| Variable | Required? | Default or example | Description |
|---|---:|---|---|
| `YOUTUBE_API_KEY` | Yes | `change_me` | YouTube Data API key |
| `YOUTUBE_API_BASE_URL` | No | `https://www.googleapis.com/youtube/v3` | YouTube API base URL |
| `YOUTUBE_DAILY_QUOTA_BUDGET` | No | `9000` | Application quota guard |
| `DATABASE_URL` | No | `sqlite:///./youtube_intel.db` | Database connection |
| `CORS_ORIGINS` | Production | Frontend URL | Allowed browser origins |
| `ENVIRONMENT` | No | `development` | Runtime environment |
| `DEBUG` | No | `false` | Debug configuration |
| `REQUEST_TIMEOUT` | No | `30` | External request timeout |
| `SNAPSHOT_SYNC_ENABLED` | No | `false` | Enables background snapshots |
| `SNAPSHOT_SYNC_INTERVAL_HOURS` | No | `6` | Snapshot interval |
| `GOOGLE_OAUTH_CLIENT_ID` | Optional | Empty | Google OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Optional | Empty | Google OAuth secret |
| `GOOGLE_OAUTH_REDIRECT_URI` | Optional | Local callback | OAuth redirect URL |

### Frontend Variables

| Variable | Required? | Description |
|---|---:|---|
| `VITE_API_BASE_URL` | Production | Public Render backend URL |

## YouTube API Configuration

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Open **APIs & Services**.
4. Enable **YouTube Data API v3**.
5. Open **Credentials**.
6. Create an API key.
7. Restrict the key to the YouTube Data API where possible.
8. Store the key inside `backend/.env`.
9. Add the key as a protected Render environment variable during deployment.

Never commit your real API key.

## Backend Deployment on Render

The repository contains a root-level `render.yaml`.

1. Sign in to Render using GitHub.
2. Select **New → Blueprint**.
3. Connect the `eddytiya/YT` repository.
4. Select the `main` branch.
5. Use `render.yaml` as the Blueprint file.
6. Select the free plan.
7. Enter the protected environment variables.
8. Deploy the service.

Recommended initial values:

```env
DATABASE_URL=sqlite:///./youtube_intel.db
CORS_ORIGINS=http://localhost:5175
SNAPSHOT_SYNC_ENABLED=false
```

Add the real YouTube API key through the Render dashboard.

After deployment, verify:

```text
https://your-service.onrender.com/
https://your-service.onrender.com/status
https://your-service.onrender.com/docs
```

## Frontend Deployment on Vercel

1. Sign in to Vercel using GitHub.
2. Import the `eddytiya/YT` repository.
3. Set the root directory to `frontend`.
4. Add the environment variable:

```env
VITE_API_BASE_URL=https://your-service.onrender.com
```

5. Deploy the project.
6. Copy the final Vercel URL.
7. Open the Render dashboard.
8. Change `CORS_ORIGINS` to the Vercel URL.
9. Redeploy the Render backend.

Example:

```env
CORS_ORIGINS=https://your-project.vercel.app
```

## API Documentation

FastAPI generates interactive API documentation automatically.

```text
Local:
http://localhost:8010/docs

Production:
https://your-service.onrender.com/docs
```

Representative endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/status` | API configuration and quota |
| `GET` | `/search` | YouTube search |
| `GET` | `/discover/trend-radar` | Topic trend scanning |
| `GET` | `/discover/opportunities` | Content-gap detection |
| `GET` | `/discover/creator-network` | Creator-network graph |
| `GET` | `/analyze/video/{video_id}` | Combined video analysis |
| `GET` | `/analyze/thumbnail` | Thumbnail analysis |
| `GET` | `/analyze/channel-audit/{channel_id}` | Channel audit |
| `GET` | `/predict/virality/{video_id}` | Virality prediction |
| `GET` | `/predict/channel-growth/{channel_id}` | Growth forecast |
| `POST` | `/create/titles` | Title generation |
| `GET` | `/monitor/sentiment/{video_id}` | Sentiment snapshot |
| `GET` | `/recommend/similar/{video_id}` | Similar videos |
| `POST` | `/track/channels` | Track a channel |
| `POST` | `/track/videos` | Track a video |
| `GET` | `/track/digest` | Tracking summary |

## YouTube Quota Management

The YouTube Data API uses a quota system.

The application includes:

- A visible quota meter
- A configurable daily budget
- A soft in-process quota guard
- Quota-aware error messages
- Reuse of already fetched data where possible

Search operations consume more quota than standard video or channel lookups.

The default application budget is:

```env
YOUTUBE_DAILY_QUOTA_BUDGET=9000
```

This remains below Google’s standard daily allowance and provides a safety margin.

## Persistence and Free-Tier Behaviour

SQLite is used by default because it makes local setup simple.

On Render’s free web-service tier, local filesystem data should be treated as temporary. Tracking data may disappear after:

- A redeployment
- A service restart
- An instance replacement
- Infrastructure maintenance

For persistent production tracking, configure `DATABASE_URL` with PostgreSQL.

The project already includes:

- SQLAlchemy-based persistence
- PostgreSQL driver support
- Repository-layer database operations

The free Render backend may also sleep during inactivity. The first request after sleep can take longer.

## Google OAuth

Google OAuth is optional.

It allows the owner of a YouTube channel to connect their account and retrieve private metrics that are not available through the public YouTube Data API.

These can include:

- Watch time
- Subscriber changes
- Creator-only analytics

OAuth cannot retrieve MrBeast’s private analytics unless MrBeast authorizes the application.

Required variables:

```env
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=
```

The public-data features work without OAuth.

## Model and Analytics Limitations

The generated scores and forecasts are analytical signals, not guaranteed outcomes.

Important limitations:

- Sentiment uses a weighted lexicon rather than a transformer model.
- Thumbnail analysis uses image heuristics.
- Virality scoring is not a guarantee of future views.
- ARIMA requires sufficient historical snapshots.
- Random Forest training requires enough tracked videos.
- Creator networks are inferred from fetched titles and keywords.
- The creator graph is not YouTube’s private recommendation network.
- TF-IDF search is text similarity, not neural embedding search.
- Comment analysis depends on comments being public and enabled.
- Live-chat analysis requires an active livestream.
- Translation depends on an external best-effort translation service.
- YouTube API results and availability can change.

The application clearly displays heuristic fallbacks when there is insufficient data for a trained model.

## Security

- Never commit `backend/.env`.
- Never commit your YouTube API key.
- Never expose an OAuth client secret in frontend code.
- Store production secrets only in Render environment variables.
- Restrict Google API credentials where possible.
- Keep database files out of Git.
- Configure production CORS carefully.
- Do not use wildcard CORS origins for credentialed production requests.
- Review API quota usage regularly.

The repository ignores:

```text
backend/.env
backend/youtube_intel.db
.venv/
node_modules/
frontend/dist/
*.log
*.tmp
.claude/
.impeccable/
```

## Current Verification Status

The project has been verified locally with the following checks:

- Frontend production build succeeds.
- React and Vite dependencies install correctly.
- Backend Python modules compile successfully.
- FastAPI imports successfully.
- Frontend returns HTTP 200.
- Backend returns HTTP 200.
- API documentation loads correctly.
- All API routes are registered.
- CORS works between frontend and backend.
- Representative live YouTube workflows work.
- Video analysis works.
- Thumbnail analysis works.
- Sentiment analysis works.
- Virality prediction works.
- Channel-growth forecasting works.
- Title generation works.
- Recommendations work.
- Tracking database reads work.
- Dependency checks report no conflicts.

The repository does not currently contain a complete automated test suite.

## Future Improvements

Potential improvements include:

- Add backend unit and integration tests.
- Add frontend component tests.
- Add GitHub Actions CI.
- Add persistent PostgreSQL hosting.
- Add response caching.
- Add durable scheduled background jobs.
- Improve model evaluation with out-of-sample datasets.
- Add authentication and multi-user support.
- Add stronger rate limiting.
- Add centralized logs and monitoring.
- Add a custom domain.
- Add uptime monitoring for portfolio demonstrations.
- Improve mobile layouts.
- Add accessibility testing.
- Add deployment-preview checks.

## Project Purpose

Reel Oracle was created as a full-stack portfolio project to demonstrate skills in:

- Frontend development
- Backend API development
- Third-party API integration
- Database design
- Data analysis
- Natural-language processing
- Machine learning
- Time-series forecasting
- Graph analysis
- Responsive UI design
- Cloud deployment
- Security-conscious configuration
- Technical product design

## Author

Built by **Aditya Pathak**.

- GitHub: [@eddytiya](https://github.com/eddytiya)
- Repository: [github.com/eddytiya/YT](https://github.com/eddytiya/YT)

## License

No open-source license has been selected yet.

Unless a license is added, the source code remains under the author’s default copyright.

---

If you find this project useful or interesting, consider starring the repository.
