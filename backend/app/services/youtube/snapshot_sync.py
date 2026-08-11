"""Background poller that snapshots tracked channels/videos into history tables.

Deliberately avoids search.list (100 units) entirely - every call here costs
1-2 units, so tracking dozens of channels/videos on a several-hour interval
stays a small fraction of the daily quota budget.
"""

import logging

from sqlalchemy.orm import Session

from app.repositories.tracking_repository import TrackingRepository
from app.services.youtube import analytics, sentiment as sentiment_engine
from app.services.youtube.resources import (
    get_channel_recent_videos,
    get_channels,
    get_comment_threads,
    get_videos,
)

logger = logging.getLogger(__name__)


def _snapshot_channel(repo: TrackingRepository, channel_id: str):
    channels = get_channels([channel_id])
    if not channels:
        logger.warning("Tracked channel not found, skipping: %s", channel_id)
        return
    channel = channels[0]
    stats = channel.get("statistics", {})

    recent = get_channel_recent_videos(channel_id, max_results=10)
    avg_views_per_day = (
        sum(analytics.engagement_metrics(v)["views_per_day"] for v in recent) / len(recent)
        if recent else 0.0
    )

    repo.save_channel_snapshot(
        channel_id,
        subscribers=int(stats.get("subscriberCount", 0) or 0),
        total_views=int(stats.get("viewCount", 0) or 0),
        video_count=int(stats.get("videoCount", 0) or 0),
        avg_views_per_day_recent=round(avg_views_per_day, 1),
    )


def _snapshot_video(repo: TrackingRepository, video_id: str):
    videos = get_videos([video_id])
    if not videos:
        logger.warning("Tracked video not found, skipping: %s", video_id)
        return
    video = videos[0]
    stats = video.get("statistics", {})
    channel_id = video.get("snippet", {}).get("channelId")
    channel = get_channels([channel_id])[0] if channel_id else None

    virality = analytics.virality_score(video, channel)

    try:
        threads = get_comment_threads(video_id, max_results=30)
        sentiment = sentiment_engine.analyze_comments(threads)
        positive_pct = sentiment.get("overall_positive_pct")
        toxicity_pct = sentiment.get("toxicity_pct")
    except Exception:
        positive_pct = None
        toxicity_pct = None

    repo.save_video_snapshot(
        video_id,
        views=int(stats.get("viewCount", 0) or 0),
        likes=int(stats.get("likeCount", 0) or 0),
        comments=int(stats.get("commentCount", 0) or 0),
        virality_score=virality["virality_score"],
        positive_pct=positive_pct,
        toxicity_pct=toxicity_pct,
    )


def run_snapshot_sync(db: Session) -> dict:
    repo = TrackingRepository(db)
    channels_done = channels_failed = 0
    videos_done = videos_failed = 0

    for tracked in repo.list_tracked_channels():
        channel_id = tracked.channel_id
        try:
            _snapshot_channel(repo, channel_id)
            channels_done += 1
        except Exception:
            logger.exception("Channel snapshot failed: %s", channel_id)
            channels_failed += 1
            db.rollback()

    for tracked in repo.list_tracked_videos():
        video_id = tracked.video_id
        try:
            _snapshot_video(repo, video_id)
            videos_done += 1
        except Exception:
            logger.exception("Video snapshot failed: %s", video_id)
            videos_failed += 1
            db.rollback()

    return {
        "channels_snapshotted": channels_done,
        "channels_failed": channels_failed,
        "videos_snapshotted": videos_done,
        "videos_failed": videos_failed,
    }
