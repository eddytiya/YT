"""Derived-from-stored-history features: leaderboards, milestone detection,
and channel comparisons. Everything here operates on snapshot rows already
sitting in the tracking database from the background poller - zero
additional YouTube API calls, no matter how often these are called."""

MILESTONE_SUBSCRIBER_THRESHOLDS = [1_000, 10_000, 100_000, 500_000, 1_000_000, 10_000_000]
VIRALITY_JUMP_POINTS = 15.0
SENTIMENT_SWING_POINTS = 15.0

CHANNEL_METRICS = {"subscribers", "subscriber_change", "avg_views_per_day_recent", "total_views"}
VIDEO_METRICS = {"views", "view_change", "virality_score", "virality_change", "positive_pct"}


def _delta(curr, prev, attr):
    a, b = getattr(curr, attr, None), getattr(prev, attr, None)
    if a is None or b is None:
        return None
    return a - b


def build_channel_row(tracked, history: list) -> dict:
    latest = history[-1] if history else None
    previous = history[-2] if len(history) > 1 else None
    return {
        "channel_id": tracked.channel_id,
        "label": tracked.label,
        "subscribers": latest.subscribers if latest else None,
        "subscriber_change": _delta(latest, previous, "subscribers") if latest and previous else None,
        "avg_views_per_day_recent": latest.avg_views_per_day_recent if latest else None,
        "total_views": latest.total_views if latest else None,
        "snapshot_count": len(history),
        "last_snapshot_at": latest.captured_at if latest else None,
    }


def build_video_row(tracked, history: list) -> dict:
    latest = history[-1] if history else None
    previous = history[-2] if len(history) > 1 else None
    return {
        "video_id": tracked.video_id,
        "label": tracked.label,
        "views": latest.views if latest else None,
        "view_change": _delta(latest, previous, "views") if latest and previous else None,
        "virality_score": latest.virality_score if latest else None,
        "virality_change": _delta(latest, previous, "virality_score") if latest and previous else None,
        "positive_pct": latest.positive_pct if latest else None,
        "toxicity_pct": latest.toxicity_pct if latest else None,
        "snapshot_count": len(history),
        "last_snapshot_at": latest.captured_at if latest else None,
    }


def rank(rows: list[dict], metric: str, limit: int) -> list[dict]:
    ranked = sorted((r for r in rows if r.get(metric) is not None), key=lambda r: r[metric], reverse=True)
    return ranked[:limit]


def detect_channel_milestones(tracked, history: list) -> list[dict]:
    """Crossing a round subscriber threshold between two consecutive
    snapshots. Only fires once per threshold, the moment it's crossed."""
    events = []
    for i in range(1, len(history)):
        prev, curr = history[i - 1], history[i]
        for threshold in MILESTONE_SUBSCRIBER_THRESHOLDS:
            if prev.subscribers < threshold <= curr.subscribers:
                events.append({
                    "kind": "subscriber_milestone",
                    "channel_id": tracked.channel_id,
                    "label": tracked.label,
                    "message": f"Crossed {threshold:,} subscribers",
                    "captured_at": curr.captured_at,
                })
    return events


def detect_video_milestones(tracked, history: list) -> list[dict]:
    """Meaningful swings between two consecutive snapshots - a jump/drop in
    virality score, or a swing in audience sentiment."""
    events = []
    for i in range(1, len(history)):
        prev, curr = history[i - 1], history[i]
        if curr.virality_score is not None and prev.virality_score is not None:
            jump = curr.virality_score - prev.virality_score
            if abs(jump) >= VIRALITY_JUMP_POINTS:
                events.append({
                    "kind": "virality_shift",
                    "video_id": tracked.video_id,
                    "label": tracked.label,
                    "message": f"Virality score {'jumped' if jump > 0 else 'dropped'} {abs(jump):.0f} points",
                    "captured_at": curr.captured_at,
                })
        if curr.positive_pct is not None and prev.positive_pct is not None:
            swing = curr.positive_pct - prev.positive_pct
            if abs(swing) >= SENTIMENT_SWING_POINTS:
                events.append({
                    "kind": "sentiment_shift",
                    "video_id": tracked.video_id,
                    "label": tracked.label,
                    "message": f"Audience sentiment {'improved' if swing > 0 else 'declined'} {abs(swing):.0f} points",
                    "captured_at": curr.captured_at,
                })
    return events
