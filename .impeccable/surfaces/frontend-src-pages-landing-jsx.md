---
version: 1
slug: "frontend-src-pages-landing-jsx"
primary_target: "frontend/src/pages/Landing.jsx"
related_targets: []
---

# Surface: Landing (`/`)

**Scope**: The public-facing entry point at `/`, in front of the existing dashboard app (now at `/app`). Visitor mode: Persuade.

**Audience & job**: A prospective client sent this link directly by the developer, deciding in seconds whether this person is worth hiring, then wanting to see the real tool work. Not a cold-traffic/ad-funnel visitor — no pricing, no signup, no urgency copy.

**Structure**: "The Case Files Drawer" — assigned via `concept-seed.mjs --scope surface --mode persuade` (seed key `cb77ae27`, candidate 6 of 7 own-list). A horizontal rail of case-file tabs (Overview + the 7 real product pillars + Who/Method/Log), not a vertical stack of marketing sections. Deliberately reuses the app's own Discover/Analyse/Predict/Create/Monitor/Recommend/Tracking pillar names as the tabs, so the landing page and the real tool read as the same object.

**Content/proof**: Every pillar file's "exhibits" are real, specific technical capabilities already shipped in the backend (burst z-score, TF-IDF re-rank, RandomForest/ARIMA, etc.) — no invented usage stats, no fake testimonials, consistent with PRODUCT.md's "Evidence on Hand" constraint. The intake ticket (analyze video/channel/discover topics/compare creators) is functionally real: submitting it navigates into `/app` with the tab and field pre-loaded via a one-shot `sessionStorage` handoff, not a decorative mockup.

**Chosen direction**: Same committed world as the dashboard (Field Intelligence Dossier — oxblood accent, cut-corner clip-path, Oswald/Inter/Courier Prime). Two new fluid type roles added to DESIGN.md for this surface only (Hero Display, Section Head) since a Persuade first viewport needs viewport-responsive scale the fixed Operate scale doesn't.

**Memorable moment**: The intake ticket actually working — submitting a real video/channel ID from the landing page opens the live tool already mid-analysis, proving the pitch instead of just stating it.

**Unresolved / open**: No real usage numbers exist yet (videos analyzed, time saved, etc.) — the Case Log file deliberately lists real technical capabilities instead of fabricating metrics. Revisit if real usage data becomes available later.
