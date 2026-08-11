import asyncio
import contextlib
import csv
import io
import logging
import secrets
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.repositories.tracking_repository import TrackingRepository
from app.services.youtube import analytics
from app.services.youtube import bot_detection
from app.services.youtube import graph_analysis
from app.services.youtube import ml_models
from app.services.youtube import oauth as oauth_service
from app.services.youtube.client import YouTubeNotConfiguredError, YouTubeQuotaGuardError, youtube_client
from app.services.youtube import sentiment as sentiment_engine
from app.services.youtube import tracking_insights
from app.services.youtube.resources import (
    get_active_live_chat_id,
    get_channel_recent_videos,
    get_channel_sections,
    get_channels,
    get_comment_threads,
    get_i18n_languages,
    get_i18n_regions,
    get_live_chat_messages,
    get_playlist_items_full,
    get_trending_videos,
    get_video_categories,
    get_videos,
    resolve_channel_id,
    search_videos,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["YouTube"])

# Short-lived OAuth CSRF state store: state -> expiry epoch seconds.
_oauth_state_store: dict[str, float] = {}
_OAUTH_STATE_TTL_SECONDS = 600


def _run(label: str, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except YouTubeNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except YouTubeQuotaGuardError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except HTTPException:
        raise
    except Exception:
        logger.exception("YouTube module call failed: %s", label)
        raise HTTPException(status_code=502, detail=f"YouTube request failed: {label}")


def _split_ids(raw: str) -> list[str]:
    return [v.strip() for v in raw.split(",") if v.strip()]


def _one_video(video_id: str) -> dict:
    items = get_videos([video_id])
    if not items:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")
    return items[0]


def _one_channel(channel_id: str) -> dict:
    items = get_channels([channel_id])
    if not items:
        raise HTTPException(status_code=404, detail=f"Channel not found: {channel_id}")
    return items[0]


def _resolve_channel_or_400(raw: str) -> str:
    """Turns a pasted channel URL, @handle, or raw ID into a real channel
    ID - used as a FastAPI dependency so every channel_id/own_channel_id
    param gets this for free instead of only accepting a bare UC... ID."""
    try:
        return resolve_channel_id(raw)
    except YouTubeNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except YouTubeQuotaGuardError as exc:
        raise HTTPException(status_code=429, detail=str(exc))


def resolved_channel_id(channel_id: str) -> str:
    return _resolve_channel_or_400(channel_id)


def resolved_own_channel_id(own_channel_id: str) -> str:
    return _resolve_channel_or_400(own_channel_id)


def _resolve_channel_ids_csv(raw: str) -> list[str]:
    """Same URL/@handle/raw-ID resolution as the single-channel dependency,
    applied to a comma-separated list (competitor IDs, channel comparisons)."""
    return [_resolve_channel_or_400(v) for v in _split_ids(raw)]


@router.get("/status")
def get_status():
    return {
        "configured": bool(settings.YOUTUBE_API_KEY),
        "quota": youtube_client.quota_status(),
        "oauth_configured": oauth_service.is_configured(),
    }


# --------------------------------------------------------------------------
# Raw resource access
# --------------------------------------------------------------------------


@router.get("/search")
def search(
    q: str = Query(..., min_length=1, max_length=100),
    max_results: int = Query(default=10, ge=1, le=50),
    order: str = Query(default="relevance", pattern="^(relevance|date|rating|viewCount|title)$"),
    event_type: str | None = Query(default=None, pattern="^(live|upcoming|completed)$"),
    video_duration: str | None = Query(default=None, pattern="^(short|medium|long)$"),
    safe_search: str | None = Query(default=None, pattern="^(none|moderate|strict)$"),
    video_definition: str | None = Query(default=None, pattern="^(standard|high)$"),
    relevance_language: str | None = Query(default=None, min_length=2, max_length=5),
):
    def compute():
        return search_videos(
            q, max_results, order,
            event_type=event_type, video_duration=video_duration, safe_search=safe_search,
            video_definition=video_definition, relevance_language=relevance_language,
        )

    return {"items": _run("search", compute)}


@router.get("/videos")
def videos(ids: str = Query(..., description="Comma-separated video IDs")):
    video_ids = _split_ids(ids)
    if not video_ids:
        raise HTTPException(status_code=400, detail="At least one video id is required")
    return {"items": _run("videos", get_videos, video_ids)}


@router.get("/channels")
def channels(ids: str = Query(..., description="Comma-separated channel IDs")):
    channel_ids = _split_ids(ids)
    if not channel_ids:
        raise HTTPException(status_code=400, detail="At least one channel id is required")
    return {"items": _run("channels", get_channels, channel_ids)}


@router.get("/videos/{video_id}/comments")
def comments(video_id: str, max_results: int = Query(default=20, ge=1, le=100)):
    return {"items": _run("comments", get_comment_threads, video_id, max_results)}


@router.get("/trending")
def trending(
    region_code: str = Query(default="IN", min_length=2, max_length=2),
    category_id: str | None = Query(default=None),
    max_results: int = Query(default=20, ge=1, le=50),
):
    return {"items": _run("trending", get_trending_videos, region_code, category_id, max_results)}


@router.get("/channels/{channel_id}/recent-videos")
def channel_recent_videos(channel_id: str = Depends(resolved_channel_id), max_results: int = Query(default=20, ge=1, le=50)):
    return {"items": _run("channel_recent_videos", get_channel_recent_videos, channel_id, max_results)}


# --------------------------------------------------------------------------
# 1. DISCOVER
# --------------------------------------------------------------------------


@router.get("/discover/trend-radar")
def discover_trend_radar(
    topics: str = Query(..., description="Comma-separated topics to scan"),
    max_results: int = Query(default=15, ge=5, le=50),
    region_code: str | None = Query(default=None, min_length=2, max_length=2),
    category_id: str | None = Query(default=None),
    video_duration: str | None = Query(default=None, pattern="^(short|medium|long)$"),
):
    def compute():
        results = []
        for topic in _split_ids(topics):
            search_items = search_videos(
                topic, max_results=max_results, order="date",
                region_code=region_code, category_id=category_id, video_duration=video_duration,
            )
            video_ids = [
                item["id"]["videoId"]
                for item in search_items
                if item.get("id", {}).get("kind") == "youtube#video"
            ]
            details = get_videos(video_ids) if video_ids else []
            results.append(analytics.trend_momentum(topic, search_items, details))
        return sorted(results, key=lambda r: r["momentum_score"], reverse=True)

    return {"topics": _run("discover_trend_radar", compute)}


@router.get("/video-categories")
def video_categories(region_code: str = Query(default="US", min_length=2, max_length=2)):
    return {"items": _run("video_categories", get_video_categories, region_code)}


@router.get("/discover/opportunities")
def discover_opportunities(
    own_channel_id: str = Depends(resolved_own_channel_id),
    competitor_channel_ids: str = Query(..., description="Comma-separated competitor channel IDs, URLs, or @handles"),
    max_results: int = Query(default=20, ge=5, le=50),
):
    def compute():
        own_videos = get_channel_recent_videos(own_channel_id, max_results)
        competitor_videos: list[dict] = []
        for cid in _resolve_channel_ids_csv(competitor_channel_ids):
            competitor_videos.extend(get_channel_recent_videos(cid, max_results))
        return analytics.content_gap(own_videos, competitor_videos)

    return _run("discover_opportunities", compute)


@router.get("/discover/competitors")
def discover_competitors(channel_ids: str = Query(..., description="Comma-separated channel IDs, URLs, or @handles")):
    def compute():
        rows = get_channels(_resolve_channel_ids_csv(channel_ids))
        return analytics.competitor_comparison(rows)

    return {"channels": _run("discover_competitors", compute)}


@router.get("/discover/content-calendar")
def discover_content_calendar(
    channel_a: str = Query(...),
    channel_b: str = Query(...),
    max_results: int = Query(default=20, ge=10, le=50),
):
    """Publish-rhythm comparison between two channels - which weekdays each
    one actually uploads on. Reuses the same recent-uploads call the
    Content Gap feature already makes, at the same 1-unit-per-channel cost."""

    def compute():
        a_id = resolve_channel_id(channel_a)
        b_id = resolve_channel_id(channel_b)
        a_uploads = get_channel_recent_videos(a_id, max_results)
        b_uploads = get_channel_recent_videos(b_id, max_results)
        return {
            "channel_a": {"channel_id": a_id, **analytics.upload_cadence(a_uploads)},
            "channel_b": {"channel_id": b_id, **analytics.upload_cadence(b_uploads)},
        }

    return _run("discover_content_calendar", compute)


@router.get("/discover/creator-network")
def discover_creator_network(
    topic: str = Query(..., min_length=1, max_length=100),
    max_results: int = Query(default=30, ge=10, le=50),
):
    """Models which channels cluster together around a topic in your own
    fetched dataset - not a reconstruction of YouTube's private recommender."""

    def compute():
        search_items = search_videos(topic, max_results=max_results, order="relevance")
        return graph_analysis.build_creator_network(search_items)

    return _run("discover_creator_network", compute)


@router.get("/discover/topic-intelligence")
def discover_topic_intelligence(
    query: str = Query(..., min_length=1, max_length=100),
    competitors: str = Query(default="", description="Comma-separated competitor/product names to count mentions of"),
    max_results: int = Query(default=8, ge=3, le=15),
    comments_per_video: int = Query(default=30, ge=10, le=50),
):
    """Product review / movie-trailer style report: aggregate sentiment,
    aspects, purchase-intent/anticipation signals across many videos matching
    a topic (product name, movie title, event, etc.)."""

    def compute():
        search_items = search_videos(query, max_results=max_results, order="relevance")
        video_ids = [item["id"]["videoId"] for item in search_items if item.get("id", {}).get("kind") == "youtube#video"]
        videos = get_videos(video_ids) if video_ids else []

        comment_texts_by_video = {}
        for video_id in video_ids:
            try:
                threads = get_comment_threads(video_id, comments_per_video)
                comment_texts_by_video[video_id] = [sentiment_engine.flatten_comment_text(t) for t in threads]
            except Exception:
                comment_texts_by_video[video_id] = []

        competitor_names = _split_ids(competitors)
        return analytics.topic_intelligence_report(query, videos, comment_texts_by_video, competitor_names)

    return _run("discover_topic_intelligence", compute)


@router.get("/discover/semantic-search")
def discover_semantic_search(
    q: str = Query(..., min_length=1, max_length=150),
    max_results: int = Query(default=15, ge=5, le=50),
):
    """TF-IDF re-ranking of YouTube's own search results by text similarity
    to the full query, instead of relying only on YouTube's relevance order -
    a lightweight "meaning aware" search, not real embeddings."""

    def compute():
        items = search_videos(q, max_results=max_results, order="relevance")
        return analytics.semantic_rerank(q, items)

    return {"items": _run("discover_semantic_search", compute)}


@router.get("/discover/live-now")
def discover_live_now(
    topic: str = Query(..., min_length=1, max_length=100),
    max_results: int = Query(default=15, ge=5, le=50),
):
    """Find videos currently live for a topic - feeds directly into
    /monitor/live-chat/{video_id} without needing a video ID up front."""

    def compute():
        return search_videos(topic, max_results=max_results, order="viewCount", event_type="live")

    return {"items": _run("discover_live_now", compute)}


@router.get("/discover/upcoming")
def discover_upcoming(
    topic: str = Query(..., min_length=1, max_length=100),
    max_results: int = Query(default=15, ge=5, le=50),
):
    """Scheduled premieres/upcoming streams for a topic - release-anticipation
    tracking, e.g. an upcoming trailer premiere or product launch stream."""

    def compute():
        return search_videos(topic, max_results=max_results, order="date", event_type="upcoming")

    return {"items": _run("discover_upcoming", compute)}


@router.get("/channel-sections/{channel_id}")
def channel_sections(channel_id: str = Depends(resolved_channel_id)):
    return {"items": _run("channel_sections", get_channel_sections, channel_id)}


@router.get("/i18n/regions")
def i18n_regions():
    return {"items": _run("i18n_regions", get_i18n_regions)}


@router.get("/i18n/languages")
def i18n_languages():
    return {"items": _run("i18n_languages", get_i18n_languages)}


# --------------------------------------------------------------------------
# 2. ANALYSE
# --------------------------------------------------------------------------


@router.get("/analyze/video/{video_id}")
def analyze_video(video_id: str):
    def compute():
        video = _one_video(video_id)
        channel_id = video.get("snippet", {}).get("channelId")
        channel = _one_channel(channel_id) if channel_id else None
        engagement = analytics.engagement_metrics(video)
        try:
            threads = get_comment_threads(video_id, max_results=50)
            comment_texts = [sentiment_engine.flatten_comment_text(t) for t in threads]
            comment_sentiment = sentiment_engine.analyze_comments(threads)
            aspects = sentiment_engine.analyze_aspects(comment_texts)
            # Same fetched batch as sentiment/aspects above - no extra API call.
            topics = analytics.cluster_comment_topics(comment_texts)
        except Exception:
            comment_sentiment = {"error": "comments unavailable or disabled for this video"}
            aspects = {}
            topics = []
        return {
            "video": {
                "id": video.get("id"),
                "title": video.get("snippet", {}).get("title"),
                "channel_title": video.get("snippet", {}).get("channelTitle"),
                "published_at": video.get("snippet", {}).get("publishedAt"),
                "thumbnail": video.get("snippet", {}).get("thumbnails", {}).get("high", {}).get("url"),
            },
            "engagement": engagement,
            "comment_sentiment": comment_sentiment,
            "aspects": aspects,
            "topics": topics,
            "virality": analytics.virality_score(video, channel),
        }

    return _run("analyze_video", compute)


@router.get("/analyze/comments/{video_id}")
def analyze_comments(
    video_id: str,
    max_results: int = Query(default=50, ge=10, le=100),
    multilingual: bool = Query(default=False, description="Detect + translate non-English comments before scoring (slower)"),
):
    def compute():
        threads = get_comment_threads(video_id, max_results)
        result = (
            sentiment_engine.analyze_comments_multilingual(threads)
            if multilingual
            else sentiment_engine.analyze_comments(threads)
        )
        # Topic clusters run on the same fetched batch - no extra API calls.
        texts = [sentiment_engine.flatten_comment_text(item) for item in threads]
        result["topics"] = analytics.cluster_comment_topics(texts)
        return result

    return _run("analyze_comments", compute)


@router.get("/analyze/aspects/{video_id}")
def analyze_aspects(video_id: str, max_results: int = Query(default=50, ge=10, le=100)):
    def compute():
        threads = get_comment_threads(video_id, max_results)
        texts = [sentiment_engine.flatten_comment_text(t) for t in threads]
        return {"aspects": sentiment_engine.analyze_aspects(texts)}

    return _run("analyze_aspects", compute)


@router.get("/analyze/misleading/{video_id}")
def analyze_misleading(video_id: str, max_results: int = Query(default=50, ge=10, le=100)):
    def compute():
        video = _one_video(video_id)
        threads = get_comment_threads(video_id, max_results)
        comment_texts = [sentiment_engine.flatten_comment_text(t) for t in threads]
        return analytics.detect_misleading(video, comment_texts)

    return _run("analyze_misleading", compute)


@router.get("/analyze/brand-safety/{channel_id}")
def analyze_brand_safety(channel_id: str = Depends(resolved_channel_id), sample_size: int = Query(default=5, ge=2, le=10)):
    def compute():
        channel = _one_channel(channel_id)
        recent_videos = get_channel_recent_videos(channel_id, max_results=15)
        sample = recent_videos[:sample_size]
        sentiments = []
        for v in sample:
            try:
                threads = get_comment_threads(v["id"], max_results=30)
                sentiments.append(sentiment_engine.analyze_comments(threads))
            except Exception:
                continue
        return analytics.brand_safety_score(channel, sentiments, recent_videos)

    return _run("analyze_brand_safety", compute)


@router.get("/analyze/playlist/{playlist_id}")
def analyze_playlist(playlist_id: str, max_results: int = Query(default=50, ge=5, le=50)):
    def compute():
        videos = get_playlist_items_full(playlist_id, max_results)
        if not videos:
            raise HTTPException(status_code=404, detail="Playlist not found or has no videos")
        return analytics.playlist_summary(videos)

    return _run("analyze_playlist", compute)


@router.get("/analyze/thumbnail")
def analyze_thumbnail(video_id: str = Query(...)):
    def compute():
        video = _one_video(video_id)
        thumbnails = video.get("snippet", {}).get("thumbnails", {})
        url = (thumbnails.get("maxres") or thumbnails.get("high") or thumbnails.get("medium") or {}).get("url")
        if not url:
            raise HTTPException(status_code=404, detail="No thumbnail available for this video")
        return analytics.analyze_thumbnail(url)

    return _run("analyze_thumbnail", compute)


@router.get("/analyze/bot-risk/{video_id}")
def analyze_bot_risk(video_id: str, max_results: int = Query(default=50, ge=10, le=100)):
    def compute():
        threads = get_comment_threads(video_id, max_results)
        return bot_detection.analyze_engagement_risk(threads)

    return _run("analyze_bot_risk", compute)


@router.get("/analyze/channel-audit/{channel_id}")
def analyze_channel_audit(channel_id: str = Depends(resolved_channel_id), sample_size: int = Query(default=5, ge=2, le=10)):
    def compute():
        channel = _one_channel(channel_id)
        recent_videos = get_channel_recent_videos(channel_id, max_results=15)

        sample = recent_videos[:sample_size]
        sentiments = []
        for v in sample:
            try:
                threads = get_comment_threads(v["id"], max_results=30)
                sentiments.append(sentiment_engine.analyze_comments(threads))
            except Exception:
                continue
        brand_safety = analytics.brand_safety_score(channel, sentiments, recent_videos)
        upload_timing = analytics.best_upload_timing(recent_videos)
        growth = analytics.channel_growth_forecast(channel, recent_videos)

        audit = analytics.channel_audit(channel, recent_videos, brand_safety, upload_timing, growth)
        try:
            sections = get_channel_sections(channel_id)
        except Exception:
            sections = []
        return {**audit, "brand_safety": brand_safety, "upload_timing": upload_timing, "growth": growth, "channel_sections": sections}

    return _run("analyze_channel_audit", compute)


# --------------------------------------------------------------------------
# 3. PREDICT
# --------------------------------------------------------------------------


@router.get("/predict/virality/{video_id}")
def predict_virality(video_id: str):
    def compute():
        video = _one_video(video_id)
        channel_id = video.get("snippet", {}).get("channelId")
        channel = _one_channel(channel_id) if channel_id else None
        return analytics.virality_score(video, channel)

    return _run("predict_virality", compute)


@router.get("/predict/channel-growth/{channel_id}")
def predict_channel_growth(channel_id: str = Depends(resolved_channel_id)):
    def compute():
        channel = _one_channel(channel_id)
        recent = get_channel_recent_videos(channel_id, max_results=15)
        return analytics.channel_growth_forecast(channel, recent)

    return _run("predict_channel_growth", compute)


@router.get("/predict/virality-ml/{video_id}")
def predict_virality_ml(video_id: str, db: Session = Depends(get_db)):
    """Trains a small RandomForest on your own tracked-video history (title
    features -> virality score) and predicts this video's score with it.
    Falls back to the heuristic if you don't have enough tracked history."""

    def compute():
        repo = TrackingRepository(db)
        tracked = repo.list_tracked_videos()
        samples = []
        for row in tracked:
            history = repo.get_video_history(row.video_id, limit=365)
            if not history or history[-1].virality_score is None:
                continue
            videos = get_videos([row.video_id])
            if not videos:
                continue
            samples.append({
                "title": videos[0].get("snippet", {}).get("title", ""),
                "published_at": videos[0].get("snippet", {}).get("publishedAt"),
                "virality_score": history[-1].virality_score,
            })

        training_result = ml_models.train_virality_model(samples)
        video = _one_video(video_id)
        title = video.get("snippet", {}).get("title", "")
        published_at = video.get("snippet", {}).get("publishedAt")

        if not training_result["trained"]:
            channel_id = video.get("snippet", {}).get("channelId")
            channel = _one_channel(channel_id) if channel_id else None
            heuristic = analytics.virality_score(video, channel)
            return {**training_result, "fallback_used": "heuristic", "heuristic_result": heuristic}

        model = training_result.pop("_model")
        prediction = ml_models.predict_with_model(model, title, published_at)
        return {**training_result, "predicted_virality_score": prediction}

    return _run("predict_virality_ml", compute)


@router.get("/predict/channel-growth-ml/{channel_id}")
def predict_channel_growth_ml(channel_id: str = Depends(resolved_channel_id), db: Session = Depends(get_db)):
    """ARIMA forecast over this channel's own tracked snapshot history.
    Falls back to the heuristic forecast if there isn't enough history yet."""

    def compute():
        repo = TrackingRepository(db)
        history = repo.get_channel_history(channel_id, limit=365)
        series = [{"captured_at": h.captured_at.isoformat(), "subscribers": h.subscribers} for h in history]
        result = ml_models.forecast_subscribers_arima(series)

        if result["method"] not in ("arima",):
            channel = _one_channel(channel_id)
            recent = get_channel_recent_videos(channel_id, max_results=15)
            heuristic = analytics.channel_growth_forecast(channel, recent)
            return {**result, "fallback_used": "heuristic", "heuristic_result": heuristic}

        return result

    return _run("predict_channel_growth_ml", compute)


# --------------------------------------------------------------------------
# 4. CREATE
# --------------------------------------------------------------------------


class TitleRequest(BaseModel):
    topic: str
    style: str = "educational"


@router.post("/create/titles")
def create_titles(payload: TitleRequest):
    def compute():
        return {"variants": analytics.generate_title_variants(payload.topic, payload.style)}

    return _run("create_titles", compute)


@router.get("/create/upload-timing/{channel_id}")
def create_upload_timing(channel_id: str = Depends(resolved_channel_id), max_results: int = Query(default=30, ge=10, le=50)):
    def compute():
        uploads = get_channel_recent_videos(channel_id, max_results)
        return analytics.best_upload_timing(uploads)

    return _run("create_upload_timing", compute)


@router.get("/create/personalized-insights")
def create_personalized_insights(db: Session = Depends(get_db)):
    """Correlates title patterns with virality across your own tracked
    videos - needs a handful of tracked videos with snapshot history."""

    def compute():
        repo = TrackingRepository(db)
        tracked = repo.list_tracked_videos()
        titles, scores = [], []
        for row in tracked:
            history = repo.get_video_history(row.video_id, limit=365)
            if not history or history[-1].virality_score is None:
                continue
            videos = get_videos([row.video_id])
            if not videos:
                continue
            titles.append(videos[0].get("snippet", {}).get("title", ""))
            scores.append(history[-1].virality_score)
        return analytics.personalized_title_insights(titles, scores)

    return _run("create_personalized_insights", compute)


# --------------------------------------------------------------------------
# 5. MONITOR
# --------------------------------------------------------------------------


@router.get("/monitor/sentiment/{video_id}")
def monitor_sentiment(
    video_id: str,
    max_results: int = Query(default=50, ge=10, le=100),
    multilingual: bool = Query(default=False),
):
    """Poll-based sentiment snapshot. Not a live-chat stream - re-poll this endpoint
    on an interval from the frontend to approximate "live" monitoring."""

    def compute():
        threads = get_comment_threads(video_id, max_results)
        if multilingual:
            return sentiment_engine.analyze_comments_multilingual(threads)
        return sentiment_engine.analyze_comments(threads)

    return _run("monitor_sentiment", compute)


@router.get("/monitor/anomalies/{channel_id}")
def monitor_anomalies(channel_id: str = Depends(resolved_channel_id), max_results: int = Query(default=20, ge=5, le=50)):
    def compute():
        uploads = get_channel_recent_videos(channel_id, max_results)
        return {"anomalies": analytics.detect_anomalies(uploads)}

    return _run("monitor_anomalies", compute)


# --------------------------------------------------------------------------
# 6. RECOMMEND
# --------------------------------------------------------------------------


@router.get("/recommend/similar/{video_id}")
def recommend_similar(video_id: str, max_results: int = Query(default=10, ge=1, le=25)):
    def compute():
        video = _one_video(video_id)
        title = video.get("snippet", {}).get("title", "")
        tags = video.get("snippet", {}).get("tags", [])
        query = " ".join(tags[:3]) if tags else title
        results = search_videos(query, max_results=max_results + 1, order="relevance")
        return [r for r in results if r.get("id", {}).get("videoId") != video_id][:max_results]

    return {"items": _run("recommend_similar", compute)}


@router.get("/recommend/next-video-ideas")
def recommend_next_video_ideas(
    own_channel_id: str = Depends(resolved_own_channel_id),
    competitor_channel_ids: str = Query(..., description="Comma-separated competitor channel IDs, URLs, or @handles"),
    max_results: int = Query(default=20, ge=5, le=50),
):
    def compute():
        own_videos = get_channel_recent_videos(own_channel_id, max_results)
        competitor_videos: list[dict] = []
        for cid in _resolve_channel_ids_csv(competitor_channel_ids):
            competitor_videos.extend(get_channel_recent_videos(cid, max_results))
        gaps = analytics.content_gap(own_videos, competitor_videos)["content_gaps"]
        ideas = [
            {
                "topic": gap["keyword"],
                "why": f"competitors mention this {gap['competitor_mentions']}x, you have {gap['your_mentions']}",
                "suggested_titles": analytics.generate_title_variants(gap["keyword"], "educational")[:3],
            }
            for gap in gaps[:8]
        ]
        return {"ideas": ideas}

    return _run("recommend_next_video_ideas", compute)


# --------------------------------------------------------------------------
# 5b. MONITOR - live chat (only meaningful during an active broadcast)
# --------------------------------------------------------------------------


@router.get("/monitor/live-chat/{video_id}")
def monitor_live_chat(video_id: str, max_results: int = Query(default=200, ge=20, le=2000)):
    def compute():
        live_chat_id = get_active_live_chat_id(video_id)
        if not live_chat_id:
            raise HTTPException(status_code=404, detail="This video has no active live chat (not live, or the stream ended)")
        data = get_live_chat_messages(live_chat_id, max_results=max_results)
        messages = data.get("items", [])
        sentiment = sentiment_engine.analyze_live_chat(messages)
        return {
            "message_count": len(messages),
            "polling_interval_ms": data.get("pollingIntervalMillis"),
            "sentiment": sentiment,
            "toxicity_alert": sentiment.get("toxicity_pct", 0) > 15,
        }

    return _run("monitor_live_chat", compute)


# Free-tier safety rails for the live WebSocket stream below. This never
# runs unattended: the poll loop only exists for the lifetime of an open
# client connection, so closing the tab or losing the connection stops
# spending quota immediately. On top of that:
#   - it always waits at least as long as YouTube's own pollingIntervalMillis
#     (polling faster just burns quota on empty/duplicate pages)
#   - a hard wall-clock cap ends the session even if someone leaves a tab
#     open, so a single forgotten demo can't run indefinitely
#   - every call still goes through the shared quota-tracked client, so the
#     existing daily budget guard (YOUTUBE_DAILY_QUOTA_BUDGET) applies here
#     exactly as it does everywhere else, and ends the session gracefully
#     instead of erroring the socket
LIVE_CHAT_SESSION_LIMIT_SECONDS = 20 * 60
LIVE_CHAT_MIN_POLL_SECONDS = 4


async def _safe_send_json(websocket: WebSocket, payload: dict):
    with contextlib.suppress(Exception):
        await websocket.send_json(payload)


@router.websocket("/ws/monitor/live-chat/{video_id}")
async def ws_monitor_live_chat(websocket: WebSocket, video_id: str):
    """Pushes a sentiment/velocity tick roughly every pollingIntervalMillis
    while a stream is live and a client is connected - see the safety-rail
    notes above for why this can't run away with the daily quota.

    Passive TCP-level disconnect detection is not trustworthy enough to gate
    paid API calls on by itself - a client that vanishes without a clean
    close frame (crash, killed tab, dropped network) may not be noticed by
    the transport for a long time, and by then several extra polls could
    already have fired. So this endpoint stops on whichever comes first:
    (a) the client explicitly sends any message as a "stop" signal, which
    the frontend does the instant the user leaves this view - the primary,
    fast path for the vast majority of sessions - or (b) the hard wall-clock
    session cap below, which bounds the worst case (an ungracefully-killed
    client) to a small, known slice of the daily quota regardless of whether
    any disconnect was ever detected."""

    await websocket.accept()
    started_at = time.monotonic()
    stopped = asyncio.Event()

    async def watch_for_stop():
        with contextlib.suppress(Exception):
            await websocket.receive_text()  # any client message means "stop"
        stopped.set()

    watcher = asyncio.create_task(watch_for_stop())

    try:
        live_chat_id = await asyncio.to_thread(get_active_live_chat_id, video_id)
        if stopped.is_set():
            return
        if not live_chat_id:
            await _safe_send_json(websocket, {"type": "session_ended", "reason": "not_live"})
            return

        page_token = None
        while not stopped.is_set():
            elapsed = time.monotonic() - started_at
            if elapsed > LIVE_CHAT_SESSION_LIMIT_SECONDS:
                await _safe_send_json(websocket, {"type": "session_ended", "reason": "time_limit"})
                return

            data = await asyncio.to_thread(get_live_chat_messages, live_chat_id, page_token, 200)
            if stopped.is_set():
                break

            messages = data.get("items", [])
            page_token = data.get("nextPageToken") or page_token
            sentiment = sentiment_engine.analyze_live_chat(messages) if messages else None
            poll_seconds = max((data.get("pollingIntervalMillis") or 5000) / 1000, LIVE_CHAT_MIN_POLL_SECONDS)

            await websocket.send_json({
                "type": "tick",
                "message_count": len(messages),
                "messages_per_min": round(len(messages) / (poll_seconds / 60), 1),
                "sentiment": sentiment,
                "toxicity_alert": bool(sentiment and sentiment.get("toxicity_pct", 0) > 15),
                "quota": youtube_client.quota_status(),
                "elapsed_seconds": round(elapsed),
                "session_limit_seconds": LIVE_CHAT_SESSION_LIMIT_SECONDS,
            })

            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(stopped.wait(), timeout=poll_seconds)
    except WebSocketDisconnect:
        return
    except YouTubeQuotaGuardError:
        await _safe_send_json(websocket, {"type": "session_ended", "reason": "quota_budget_reached"})
    except YouTubeNotConfiguredError:
        await _safe_send_json(websocket, {"type": "session_ended", "reason": "not_configured"})
    except Exception:
        logger.exception("Live chat websocket failed for %s", video_id)
        await _safe_send_json(websocket, {"type": "session_ended", "reason": "error"})
    finally:
        watcher.cancel()
        with contextlib.suppress(Exception):
            await watcher
        with contextlib.suppress(Exception):
            await websocket.close()


# --------------------------------------------------------------------------
# TRACKING + HISTORY (persistence layer)
# --------------------------------------------------------------------------


class TrackChannelRequest(BaseModel):
    channel_id: str
    label: str | None = None


class TrackVideoRequest(BaseModel):
    video_id: str
    label: str | None = None


@router.post("/track/channels")
def track_channel(payload: TrackChannelRequest, db: Session = Depends(get_db)):
    channel_id = _resolve_channel_or_400(payload.channel_id)
    row = TrackingRepository(db).add_tracked_channel(channel_id, payload.label)
    return {"id": row.id, "channel_id": row.channel_id, "label": row.label}


@router.get("/track/channels")
def list_tracked_channels(db: Session = Depends(get_db)):
    rows = TrackingRepository(db).list_tracked_channels()
    return {"items": [{"id": r.id, "channel_id": r.channel_id, "label": r.label, "created_at": r.created_at} for r in rows]}


@router.delete("/track/channels/{tracked_id}")
def untrack_channel(tracked_id: int, db: Session = Depends(get_db)):
    if not TrackingRepository(db).remove_tracked_channel(tracked_id):
        raise HTTPException(status_code=404, detail="Tracked channel not found")
    return {"removed": True}


@router.post("/track/videos")
def track_video(payload: TrackVideoRequest, db: Session = Depends(get_db)):
    row = TrackingRepository(db).add_tracked_video(payload.video_id, payload.label)
    return {"id": row.id, "video_id": row.video_id, "label": row.label}


@router.get("/track/videos")
def list_tracked_videos(db: Session = Depends(get_db)):
    rows = TrackingRepository(db).list_tracked_videos()
    return {"items": [{"id": r.id, "video_id": r.video_id, "label": r.label, "created_at": r.created_at} for r in rows]}


@router.delete("/track/videos/{tracked_id}")
def untrack_video(tracked_id: int, db: Session = Depends(get_db)):
    if not TrackingRepository(db).remove_tracked_video(tracked_id):
        raise HTTPException(status_code=404, detail="Tracked video not found")
    return {"removed": True}


@router.get("/history/channel/{channel_id}")
def channel_history(channel_id: str = Depends(resolved_channel_id), limit: int = Query(default=90, ge=1, le=365), db: Session = Depends(get_db)):
    rows = TrackingRepository(db).get_channel_history(channel_id, limit)
    return {"items": [{
        "captured_at": r.captured_at,
        "subscribers": r.subscribers,
        "total_views": r.total_views,
        "video_count": r.video_count,
        "avg_views_per_day_recent": r.avg_views_per_day_recent,
    } for r in rows]}


@router.get("/history/video/{video_id}")
def video_history(video_id: str, limit: int = Query(default=90, ge=1, le=365), db: Session = Depends(get_db)):
    rows = TrackingRepository(db).get_video_history(video_id, limit)
    return {"items": [{
        "captured_at": r.captured_at,
        "views": r.views,
        "likes": r.likes,
        "comments": r.comments,
        "virality_score": r.virality_score,
        "positive_pct": r.positive_pct,
        "toxicity_pct": r.toxicity_pct,
    } for r in rows]}


def _csv_response(fieldnames: list[str], rows: list[dict], filename: str) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/history/channel/{channel_id}/export.csv")
def export_channel_history(channel_id: str = Depends(resolved_channel_id), limit: int = Query(default=365, ge=1, le=3650), db: Session = Depends(get_db)):
    rows = TrackingRepository(db).get_channel_history(channel_id, limit)
    data = [{
        "captured_at": r.captured_at.isoformat(),
        "subscribers": r.subscribers,
        "total_views": r.total_views,
        "video_count": r.video_count,
        "avg_views_per_day_recent": r.avg_views_per_day_recent,
    } for r in rows]
    return _csv_response(
        ["captured_at", "subscribers", "total_views", "video_count", "avg_views_per_day_recent"],
        data, f"channel_{channel_id}_history.csv",
    )


@router.get("/history/video/{video_id}/export.csv")
def export_video_history(video_id: str, limit: int = Query(default=365, ge=1, le=3650), db: Session = Depends(get_db)):
    rows = TrackingRepository(db).get_video_history(video_id, limit)
    data = [{
        "captured_at": r.captured_at.isoformat(),
        "views": r.views,
        "likes": r.likes,
        "comments": r.comments,
        "virality_score": r.virality_score,
        "positive_pct": r.positive_pct,
        "toxicity_pct": r.toxicity_pct,
    } for r in rows]
    return _csv_response(
        ["captured_at", "views", "likes", "comments", "virality_score", "positive_pct", "toxicity_pct"],
        data, f"video_{video_id}_history.csv",
    )


@router.get("/track/digest")
def tracking_digest(db: Session = Depends(get_db)):
    """One-shot summary of every tracked channel/video's latest known
    snapshot, so you don't have to open each one individually."""

    repo = TrackingRepository(db)

    channels_digest = []
    for tracked in repo.list_tracked_channels():
        history = repo.get_channel_history(tracked.channel_id, limit=365)
        latest = history[-1] if history else None
        previous = history[-2] if len(history) > 1 else None
        channels_digest.append({
            "channel_id": tracked.channel_id,
            "label": tracked.label,
            "latest_subscribers": latest.subscribers if latest else None,
            "subscriber_change_since_last_snapshot": (
                latest.subscribers - previous.subscribers if latest and previous else None
            ),
            "avg_views_per_day_recent": latest.avg_views_per_day_recent if latest else None,
            "last_snapshot_at": latest.captured_at if latest else None,
        })

    videos_digest = []
    for tracked in repo.list_tracked_videos():
        history = repo.get_video_history(tracked.video_id, limit=365)
        latest = history[-1] if history else None
        videos_digest.append({
            "video_id": tracked.video_id,
            "label": tracked.label,
            "latest_views": latest.views if latest else None,
            "virality_score": latest.virality_score if latest else None,
            "positive_pct": latest.positive_pct if latest else None,
            "toxicity_pct": latest.toxicity_pct if latest else None,
            "last_snapshot_at": latest.captured_at if latest else None,
        })

    return {"channels": channels_digest, "videos": videos_digest}


# The four endpoints below are all pure reads over snapshot history that's
# already sitting in the tracking database from the background poller -
# none of them make a YouTube API call, so they cost zero quota no matter
# how often the dashboard hits them.


@router.get("/track/leaderboard/channels")
def leaderboard_channels(
    metric: str = Query(default="subscriber_change"),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if metric not in tracking_insights.CHANNEL_METRICS:
        raise HTTPException(status_code=400, detail=f"metric must be one of {sorted(tracking_insights.CHANNEL_METRICS)}")
    repo = TrackingRepository(db)
    rows = [
        tracking_insights.build_channel_row(t, repo.get_channel_history(t.channel_id, limit=365))
        for t in repo.list_tracked_channels()
    ]
    return {"metric": metric, "items": tracking_insights.rank(rows, metric, limit)}


@router.get("/track/leaderboard/videos")
def leaderboard_videos(
    metric: str = Query(default="view_change"),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if metric not in tracking_insights.VIDEO_METRICS:
        raise HTTPException(status_code=400, detail=f"metric must be one of {sorted(tracking_insights.VIDEO_METRICS)}")
    repo = TrackingRepository(db)
    rows = [
        tracking_insights.build_video_row(t, repo.get_video_history(t.video_id, limit=365))
        for t in repo.list_tracked_videos()
    ]
    return {"metric": metric, "items": tracking_insights.rank(rows, metric, limit)}


@router.get("/track/milestones")
def track_milestones(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    """Notable events found by diffing consecutive snapshots: subscriber
    milestones crossed, and meaningful virality/sentiment swings."""

    repo = TrackingRepository(db)
    events: list[dict] = []
    for t in repo.list_tracked_channels():
        events.extend(tracking_insights.detect_channel_milestones(t, repo.get_channel_history(t.channel_id, limit=365)))
    for t in repo.list_tracked_videos():
        events.extend(tracking_insights.detect_video_milestones(t, repo.get_video_history(t.video_id, limit=365)))

    events.sort(key=lambda e: e["captured_at"], reverse=True)
    return {"items": events[:limit]}


@router.get("/track/compare-channels")
def compare_channels(
    channel_ids: str = Query(..., description="Comma-separated tracked channel IDs, 2-4"),
    limit: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    ids = _split_ids(channel_ids)
    if not (2 <= len(ids) <= 4):
        raise HTTPException(status_code=400, detail="Provide 2-4 comma-separated channel IDs to compare")

    repo = TrackingRepository(db)
    tracked_by_id = {t.channel_id: t for t in repo.list_tracked_channels()}
    series = []
    for cid in ids:
        tracked = tracked_by_id.get(cid)
        history = repo.get_channel_history(cid, limit=limit)
        series.append({
            "channel_id": cid,
            "label": tracked.label if tracked else cid,
            "tracked": tracked is not None,
            "history": [
                {
                    "captured_at": s.captured_at,
                    "subscribers": s.subscribers,
                    "total_views": s.total_views,
                    "avg_views_per_day_recent": s.avg_views_per_day_recent,
                }
                for s in history
            ],
        })
    return {"series": series}


# --------------------------------------------------------------------------
# OAUTH - creator-only analytics (requires GOOGLE_OAUTH_CLIENT_ID/SECRET)
# --------------------------------------------------------------------------


def _purge_expired_states():
    now = time.time()
    for state, expires_at in list(_oauth_state_store.items()):
        if expires_at < now:
            del _oauth_state_store[state]


@router.get("/oauth/status")
def oauth_status(db: Session = Depends(get_db)):
    from app.models.tracking import OAuthCredential
    connected = db.query(OAuthCredential).first()
    return {
        "configured": oauth_service.is_configured(),
        "connected": bool(connected),
        "connected_email": connected.google_account_email if connected else None,
        "connected_channel_id": connected.channel_id if connected else None,
    }


@router.get("/oauth/authorize")
def oauth_authorize():
    _purge_expired_states()
    state = secrets.token_urlsafe(24)
    _oauth_state_store[state] = time.time() + _OAUTH_STATE_TTL_SECONDS
    try:
        return {"authorize_url": oauth_service.build_authorize_url(state)}
    except oauth_service.OAuthNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/oauth/callback")
def oauth_callback(code: str | None = None, state: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    frontend_url = settings.CORS_ORIGINS.split(",")[0].strip() + "/app"

    if error:
        return RedirectResponse(f"{frontend_url}/?oauth=error&reason={error}")

    _purge_expired_states()
    if not state or state not in _oauth_state_store:
        return RedirectResponse(f"{frontend_url}/?oauth=error&reason=invalid_state")
    del _oauth_state_store[state]

    if not code:
        return RedirectResponse(f"{frontend_url}/?oauth=error&reason=missing_code")

    try:
        tokens = oauth_service.exchange_code_for_tokens(code)
        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        expires_at = datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))

        email = oauth_service.get_user_email(access_token)
        channel_id = oauth_service.get_own_channel_id(access_token)

        from app.models.tracking import OAuthCredential
        existing = db.query(OAuthCredential).first()
        if existing:
            existing.access_token = access_token
            if refresh_token:
                existing.refresh_token = refresh_token
            existing.token_expires_at = expires_at
            existing.google_account_email = email
            existing.channel_id = channel_id
            existing.scope = tokens.get("scope")
        else:
            if not refresh_token:
                return RedirectResponse(f"{frontend_url}/?oauth=error&reason=no_refresh_token")
            db.add(OAuthCredential(
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=expires_at,
                google_account_email=email,
                channel_id=channel_id,
                scope=tokens.get("scope"),
            ))
        db.commit()
        return RedirectResponse(f"{frontend_url}/?oauth=success")
    except Exception:
        logger.exception("YouTube OAuth callback failed")
        return RedirectResponse(f"{frontend_url}/?oauth=error&reason=exchange_failed")


@router.delete("/oauth/disconnect")
def oauth_disconnect(db: Session = Depends(get_db)):
    from app.models.tracking import OAuthCredential
    deleted = db.query(OAuthCredential).delete()
    db.commit()
    return {"disconnected": bool(deleted)}


def _get_valid_access_token(db: Session) -> tuple[str, str]:
    from app.models.tracking import OAuthCredential
    credential = db.query(OAuthCredential).first()
    if not credential:
        raise HTTPException(status_code=404, detail="No connected YouTube account. Visit /oauth/authorize first.")

    if credential.token_expires_at <= datetime.utcnow() + timedelta(minutes=2):
        tokens = oauth_service.refresh_access_token(credential.refresh_token)
        credential.access_token = tokens["access_token"]
        credential.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600))
        db.commit()

    return credential.access_token, credential.channel_id


@router.get("/oauth/analytics")
def oauth_analytics(days: int = Query(default=28, ge=1, le=365), db: Session = Depends(get_db)):
    def compute():
        access_token, channel_id = _get_valid_access_token(db)
        if not channel_id:
            raise HTTPException(status_code=404, detail="Connected account has no accessible YouTube channel")
        return oauth_service.get_channel_analytics(access_token, channel_id, days)

    return _run("oauth_analytics", compute)
