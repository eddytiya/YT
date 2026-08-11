# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary audience: prospective clients and collaborators the owner shares this with to demonstrate technical and product capability. Secondary: the owner themself, using it as a working sandbox against the YouTube Data API. Not built for anonymous public sign-up or multi-tenant use — it is a single-operator showcase, not a SaaS product (yet).

## Product Purpose

**Reel Oracle** is a YouTube intelligence platform that showcases what's possible when you combine the YouTube Data API with custom analytics, ML models, and NLP — trend discovery, video/channel/comment analysis, virality and growth prediction, title generation, live monitoring, and recommendation, unified in one tool. Its purpose here is portfolio-grade: it exists to prove range and depth of engineering skill to a client audience, not to serve daily production traffic.

## Positioning

Most competitor tools (TubeBuddy, VidIQ, Social Blade) each specialize in one slice — SEO, tracking, or comparison. Reel Oracle's differentiator is breadth executed to a single coherent standard: seven functional pillars (Discover, Analyse, Predict, Create, Monitor, Recommend, Tracking) built on real API data, heuristic scoring engines, trained ML models (RandomForest virality, ARIMA growth forecasting), NLP (sentiment, aspect extraction, bot-risk detection, multilingual translation, TF-IDF semantic search), and a lightweight persistence/tracking layer with snapshot history and CSV export — all in one demo a client can click through end to end.

## Operating Context

- Backend: FastAPI (Python), SQLAlchemy + SQLite/Postgres persistence, deployed via Render (`render.yaml`).
- Frontend: React + Vite, deployed via Vercel (`vercel.json`).
- Data source: YouTube Data API v3, with a visible quota-usage meter in the UI since API quota is a real constraint.
- Optional Google OAuth flow for connecting a real YouTube account to pull private Creator Analytics.
- Background snapshot-sync loop builds trend history for tracked channels/videos over time.
- Since this is demoed live to clients, the app must survive a cold, unconfigured backend gracefully (e.g. missing `YOUTUBE_API_KEY`) without looking broken.

## Capabilities and Constraints

Confirmed functional pillars (see `frontend/src/pages/YoutubeIntel.jsx` and `backend/app/api/routes.py` for the full surface):

- **Discover** — trend radar with burst detection, content-gap/competitor comparison, creator-network graph, topic intelligence (sentiment/aspects/purchase-intent aggregation), semantic (TF-IDF) search, live-now / upcoming-premiere discovery.
- **Analyse** — video intelligence (engagement, virality, sentiment, aspects), thumbnail scoring, misleading-title detection, bot/fake-engagement risk, playlist summary, brand-safety score, full channel audit.
- **Predict** — heuristic and trained-ML virality prediction; heuristic and ARIMA channel-growth forecasting (ML variants require tracked history and fall back to heuristics otherwise).
- **Create** — title generator with CTR/clickbait scoring, best upload-timing analysis, personalized title insights from the user's own tracked performance.
- **Monitor** — poll-based comment sentiment (with multilingual detect+translate), upload anomaly detection, live-chat sentiment during active broadcasts.
- **Recommend** — similar-video discovery, next-video content ideas derived from competitor gaps.
- **Tracking** — track/untrack channels and videos, historical charts, CSV export, watchlist digest, optional OAuth-connected Creator Analytics.

Constraint: quota-conscious by design (visible quota meter, guard errors); ML/ARIMA features are explicitly best-effort and degrade to heuristics — the UI must communicate that degradation honestly rather than hide it, since accuracy-with-caveats is part of the credibility story for a client audience.

## Brand Commitments

- Name: **Reel Oracle** (chosen during init; direction requested was "classy, sassy" — confident and a little playful, not corporate-flat).
- No existing logo, palette, or typography system yet — open for the next design phase (new-work) to establish.

## Evidence on Hand

No client testimonials, case studies, or sample screenshots on hand yet. All data shown is live/real YouTube API data at demo time — no fabricated sample content should be introduced.

## Product Principles

1. **Breadth is the pitch.** Every pillar should feel finished enough to click through live in front of a client — no pillar should look like an afterthought next to the others.
2. **Honesty about method builds trust.** Where a result is heuristic, ML, or degraded/fallback, say so plainly (this is already a pattern in the existing UI, e.g. "Falling back to heuristic" notes) — don't polish that language away.
3. **Survive a cold start gracefully.** Unconfigured API keys, empty tracking lists, and empty history states are first-class states a client will likely see first — they must read as intentional, not broken.
4. **Data density with clarity.** The product surfaces a lot of numbers per panel; hierarchy and scanability matter more than decoration.
5. **This is a showcase, not a scaled SaaS.** Design and build decisions should optimize for looking exceptional in a live client walkthrough over multi-tenant/production hardening.

## Accessibility & Inclusion

No specific standard mandated yet; treat standard WCAG AA as the baseline given this will be shown to external clients.
