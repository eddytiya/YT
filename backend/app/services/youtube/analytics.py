"""
Heuristic analytics on top of raw YouTube Data API responses.

None of this is a trained model - there is no historical YouTube dataset to
train against (unlike the football ML models elsewhere in this repo). Every
score here is a transparent, documented formula over numbers the API already
returns (views, likes, comments, published_at, subscriber counts). That is
weaker than a fitted model but honest about what it is, and it is still far
more useful than raw counts alone.
"""

import io
import re
from collections import Counter
from datetime import datetime, timezone

import requests
from PIL import Image, ImageFilter, ImageStat

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "this", "that", "it", "at", "by", "vs", "your",
    "you", "i", "we", "our", "how", "what", "why", "new", "video", "official",
    "full", "part", "ft", "feat", "highlights", "highlight", "2024", "2025", "2026",
}
_WORD_RE = re.compile(r"[a-zA-Z']+")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _age_days(published_at: str | None) -> float:
    dt = _parse_dt(published_at)
    if not dt:
        return 1.0
    delta = datetime.now(timezone.utc) - dt
    return max(delta.total_seconds() / 86400, 1 / 24)


def _stat_int(stats: dict, key: str) -> int:
    try:
        return int(stats.get(key, 0))
    except (TypeError, ValueError):
        return 0


# --------------------------------------------------------------------------
# ANALYSE - engagement + video intelligence
# --------------------------------------------------------------------------


def engagement_metrics(video: dict) -> dict:
    stats = video.get("statistics", {})
    views = _stat_int(stats, "viewCount")
    likes = _stat_int(stats, "likeCount")
    comments = _stat_int(stats, "commentCount")
    age_days = _age_days(video.get("snippet", {}).get("publishedAt"))

    return {
        "views": views,
        "likes": likes,
        "comments": comments,
        "age_days": round(age_days, 2),
        "views_per_day": round(views / age_days, 1),
        "like_to_view_pct": round(100 * likes / views, 3) if views else 0,
        "comment_to_view_pct": round(100 * comments / views, 3) if views else 0,
        "engagement_rate_pct": round(100 * (likes + comments) / views, 3) if views else 0,
    }


# --------------------------------------------------------------------------
# PREDICT - virality heuristic
# --------------------------------------------------------------------------


def virality_score(video: dict, channel: dict | None = None) -> dict:
    metrics = engagement_metrics(video)
    subs = _stat_int(channel.get("statistics", {}), "subscriberCount") if channel else 0

    # Each component is capped and weighted, then combined into a 0-100 score.
    # views_per_day relative to subscriber base is the strongest single signal
    # of a video overperforming its channel's normal reach.
    reach_ratio = metrics["views_per_day"] / max(subs, 1000) if subs else metrics["views_per_day"] / 50000
    reach_component = min(reach_ratio * 40, 45)

    engagement_component = min(metrics["engagement_rate_pct"] * 6, 30)

    comment_velocity = metrics["comments"] / metrics["age_days"]
    velocity_component = min((comment_velocity / 50) * 25, 25)

    score = round(reach_component + engagement_component + velocity_component, 1)
    score = max(0.0, min(score, 100.0))

    if score >= 75:
        classification = "highly likely to outperform channel average"
    elif score >= 50:
        classification = "likely to outperform channel average"
    elif score >= 25:
        classification = "tracking near channel average"
    else:
        classification = "underperforming typical reach"

    projected_7d_low = round(metrics["views"] + metrics["views_per_day"] * 7 * 0.7)
    projected_7d_high = round(metrics["views"] + metrics["views_per_day"] * 7 * 1.4)

    return {
        "virality_score": score,
        "classification": classification,
        "projected_views_7d_range": [projected_7d_low, projected_7d_high],
        "basis": "heuristic score from views/day, engagement rate and comment velocity - not a trained model",
        "metrics": metrics,
    }


def channel_growth_forecast(channel: dict, recent_videos: list[dict]) -> dict:
    stats = channel.get("statistics", {})
    subs = _stat_int(stats, "subscriberCount")
    total_views = _stat_int(stats, "viewCount")
    video_count = _stat_int(stats, "videoCount") or 1

    if recent_videos:
        avg_views_per_day = sum(engagement_metrics(v)["views_per_day"] for v in recent_videos) / len(recent_videos)
    else:
        avg_views_per_day = total_views / max(video_count, 1) / 30

    # Rough subscriber conversion: ~1 new subscriber per 300-600 fresh views,
    # tightened/loosened by the channel's existing engagement quality.
    if recent_videos:
        avg_engagement = sum(engagement_metrics(v)["engagement_rate_pct"] for v in recent_videos) / len(recent_videos)
    else:
        avg_engagement = 2.0
    conversion_rate = max(1 / 600, min(1 / 300, avg_engagement / 100 * 0.15))

    daily_new_subs = avg_views_per_day * conversion_rate
    forecast_30d = round(subs + daily_new_subs * 30)

    return {
        "current_subscribers": subs,
        "estimated_subscribers_30d": [round(forecast_30d * 0.85), round(forecast_30d * 1.15)],
        "avg_views_per_day_recent": round(avg_views_per_day, 1),
        "basis": "heuristic projection from recent upload pace and engagement - not a trained model",
    }


# --------------------------------------------------------------------------
# DISCOVER - trend radar, opportunities, competitor comparison
# --------------------------------------------------------------------------


def _detect_upload_burst(ages: list[float]) -> dict:
    """Simple change-point/burst detection over daily upload counts: buckets
    ages into days, computes a short vs long moving average, flags a burst
    when the recent rate is a statistical outlier vs the trailing baseline."""

    if not ages:
        return {"burst_detected": False, "recent_daily_rate": 0.0, "baseline_daily_rate": 0.0}

    day_buckets = Counter(int(a) for a in ages)
    max_day = max(day_buckets.keys(), default=0)
    daily_counts = [day_buckets.get(d, 0) for d in range(max_day + 1)]

    recent = daily_counts[:3]
    baseline = daily_counts[3:14] or [0]

    recent_rate = sum(recent) / max(len(recent), 1)
    baseline_rate = sum(baseline) / max(len(baseline), 1)
    baseline_std = (sum((x - baseline_rate) ** 2 for x in baseline) / max(len(baseline), 1)) ** 0.5

    z = (recent_rate - baseline_rate) / (baseline_std or 1)
    return {
        "burst_detected": z >= 1.5 and recent_rate > baseline_rate,
        "recent_daily_rate": round(recent_rate, 2),
        "baseline_daily_rate": round(baseline_rate, 2),
        "burst_z_score": round(z, 2),
    }


def trend_momentum(topic: str, search_items: list[dict], video_details: list[dict]) -> dict:
    ages = [_age_days(v.get("snippet", {}).get("publishedAt")) for v in video_details]
    recent_7d = sum(1 for a in ages if a <= 7)
    recent_30d = sum(1 for a in ages if a <= 30)

    total_views = sum(_stat_int(v.get("statistics", {}), "viewCount") for v in video_details)
    total_comments = sum(_stat_int(v.get("statistics", {}), "commentCount") for v in video_details)
    unique_channels = len({v.get("snippet", {}).get("channelId") for v in video_details})

    upload_growth_pct = round(100 * recent_7d / max(recent_30d - recent_7d, 1) - 100, 1) if recent_30d > recent_7d else 0.0
    momentum = min(100, round(recent_7d * 8 + unique_channels * 3 + min(total_views / 200000, 20), 1))
    burst = _detect_upload_burst(ages)

    return {
        "topic": topic,
        "momentum_score": momentum,
        "uploads_last_7d": recent_7d,
        "uploads_last_30d": recent_30d,
        "unique_channels_covering": unique_channels,
        "total_views_sampled": total_views,
        "total_comments_sampled": total_comments,
        "upload_growth_pct_7d_vs_prior": upload_growth_pct,
        **burst,
    }


def _extract_keywords(text: str) -> Counter:
    words = [w.lower() for w in _WORD_RE.findall(text or "")]
    return Counter(w for w in words if len(w) > 2 and w not in STOPWORDS)


def content_gap(own_videos: list[dict], competitor_videos: list[dict]) -> dict:
    own_keywords = Counter()
    for v in own_videos:
        own_keywords.update(_extract_keywords(v.get("snippet", {}).get("title", "")))

    competitor_keywords = Counter()
    for v in competitor_videos:
        competitor_keywords.update(_extract_keywords(v.get("snippet", {}).get("title", "")))

    gaps = [
        {"keyword": kw, "competitor_mentions": count, "your_mentions": own_keywords.get(kw, 0)}
        for kw, count in competitor_keywords.most_common(30)
        if own_keywords.get(kw, 0) == 0 and count >= 2
    ][:15]

    return {"content_gaps": gaps}


def competitor_comparison(channels: list[dict]) -> list[dict]:
    rows = []
    for ch in channels:
        stats = ch.get("statistics", {})
        subs = _stat_int(stats, "subscriberCount")
        views = _stat_int(stats, "viewCount")
        videos = _stat_int(stats, "videoCount") or 1
        rows.append({
            "channel_id": ch.get("id"),
            "title": ch.get("snippet", {}).get("title"),
            "subscribers": subs,
            "total_views": views,
            "video_count": videos,
            "avg_views_per_video": round(views / videos, 1),
        })
    return sorted(rows, key=lambda r: r["subscribers"], reverse=True)


# --------------------------------------------------------------------------
# CREATE - titles + upload timing
# --------------------------------------------------------------------------

CLICKBAIT_MARKERS = ["you won't believe", "shocking", "gone wrong", "insane", "!!!", "must watch", "this will"]


def score_title(title: str) -> dict:
    length = len(title)
    caps_ratio = sum(1 for c in title if c.isupper()) / max(sum(1 for c in title if c.isalpha()), 1)
    clickbait_hits = sum(1 for marker in CLICKBAIT_MARKERS if marker in title.lower())
    exclaim_count = title.count("!")

    clickbait_risk = "high" if clickbait_hits >= 2 or caps_ratio > 0.5 else "medium" if clickbait_hits == 1 or caps_ratio > 0.3 else "low"

    score = 70
    if 30 <= length <= 65:
        score += 15
    elif length > 100:
        score -= 20
    if caps_ratio < 0.3:
        score += 10
    else:
        score -= 15
    if clickbait_hits == 0:
        score += 5
    else:
        score -= 10 * clickbait_hits
    score = max(0, min(100, score))

    return {
        "title": title,
        "length": length,
        "predicted_ctr_class": "above average" if score >= 75 else "average" if score >= 50 else "below average",
        "clickbait_risk": clickbait_risk,
        "score": score,
    }


def generate_title_variants(topic: str, style: str = "educational") -> list[dict]:
    topic = topic.strip()
    if not topic:
        return []

    templates = {
        "educational": [
            "{topic}: A Complete Guide",
            "How to {topic}",
            "{topic} Explained Simply",
            "Build {topic} Step by Step",
            "{topic} for Beginners",
        ],
        "engaging": [
            "I Tried {topic} - Here's What Happened",
            "{topic}: What Nobody Tells You",
            "The Truth About {topic}",
            "{topic} in 2026",
            "Why {topic} Actually Matters",
        ],
        "news": [
            "{topic}: Breaking Down What Happened",
            "{topic} - Full Reaction",
            "Everything About {topic} You Need to Know",
            "{topic}: Analysis",
        ],
    }

    variants = [t.format(topic=topic) for t in templates.get(style, templates["educational"])]
    scored = [score_title(v) for v in variants]
    return sorted(scored, key=lambda v: v["score"], reverse=True)


def best_upload_timing(uploads: list[dict]) -> dict:
    """uploads: list of video items with snippet.publishedAt + statistics.viewCount."""

    if not uploads:
        return {"recommendation": None, "reason": "not enough upload history"}

    day_views: dict[str, list[int]] = {}
    hour_views: dict[int, list[int]] = {}

    for v in uploads:
        published = v.get("snippet", {}).get("publishedAt")
        dt = _parse_dt(published)
        if not dt:
            continue
        views = _stat_int(v.get("statistics", {}), "viewCount")
        day_name = dt.strftime("%A")
        day_views.setdefault(day_name, []).append(views)
        hour_views.setdefault(dt.hour, []).append(views)

    def _avg(mapping):
        return {k: sum(v) / len(v) for k, v in mapping.items() if v}

    day_avgs = _avg(day_views)
    hour_avgs = _avg(hour_views)

    best_day = max(day_avgs, key=day_avgs.get) if day_avgs else None
    best_hour = max(hour_avgs, key=hour_avgs.get) if hour_avgs else None

    return {
        "best_weekday": best_day,
        "best_hour_utc": best_hour,
        "avg_views_by_weekday": {k: round(v) for k, v in sorted(day_avgs.items(), key=lambda kv: -kv[1])},
        "sample_size": len(uploads),
    }


# --------------------------------------------------------------------------
# ANALYSE - thumbnail quality (pixel heuristics + Haar-cascade face detection)
# --------------------------------------------------------------------------

_face_cascade = None


def _get_face_cascade():
    global _face_cascade
    if _face_cascade is None:
        import cv2
        _face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return _face_cascade


def _detect_faces(image: "Image.Image") -> int:
    """Haar cascades are a lightweight, CPU-only classical CV method - not as
    accurate as a modern face detector, but detects clear frontal faces
    (the common thumbnail case) without needing a downloaded model file."""

    try:
        import cv2
        import numpy as np

        cascade = _get_face_cascade()
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        faces = cascade.detectMultiScale(cv_image, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        return len(faces)
    except Exception:
        return -1  # detection unavailable, distinguish from "0 faces found"


def analyze_thumbnail(thumbnail_url: str) -> dict:
    response = requests.get(thumbnail_url, timeout=10)
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content)).convert("RGB")

    width, height = image.size
    stat = ImageStat.Stat(image)
    brightness = sum(stat.mean) / 3
    # Std-dev across channels as a cheap contrast proxy.
    contrast = sum(stat.stddev) / 3

    grayscale = image.convert("L")
    edges = grayscale.filter(ImageFilter.FIND_EDGES)
    edge_stat = ImageStat.Stat(edges)
    clutter_proxy = edge_stat.mean[0]

    face_count = _detect_faces(image)

    issues = []
    if brightness < 60:
        issues.append("thumbnail is quite dark - may read poorly on mobile")
    if brightness > 220:
        issues.append("thumbnail is very bright/washed out")
    if contrast < 30:
        issues.append("low contrast - subject may not stand out")
    if clutter_proxy > 40:
        issues.append("high visual clutter detected - consider simplifying")
    if width < 1280 or height < 720:
        issues.append("resolution below the recommended 1280x720")
    if face_count == 0:
        issues.append("no clear human face detected - thumbnails with faces often get higher CTR")

    score = 100
    score -= max(0, (60 - brightness)) * 0.5
    score -= max(0, (brightness - 220)) * 0.5
    score -= max(0, (30 - contrast)) * 0.8
    score -= max(0, (clutter_proxy - 40)) * 0.6
    if face_count == 0:
        score -= 5
    score = round(max(0, min(100, score)))

    return {
        "resolution": f"{width}x{height}",
        "brightness": round(brightness, 1),
        "contrast": round(contrast, 1),
        "clutter_proxy": round(clutter_proxy, 1),
        "faces_detected": face_count if face_count >= 0 else None,
        "score": score,
        "issues": issues,
        "note": "pixel heuristics (brightness/contrast/edge density) + Haar-cascade frontal face detection - not a trained CTR model",
    }


# --------------------------------------------------------------------------
# MONITOR - anomaly detection over a channel's recent uploads
# --------------------------------------------------------------------------


def detect_anomalies(uploads: list[dict]) -> list[dict]:
    """Flag videos whose views/day is a statistical outlier vs the channel's own median."""

    if len(uploads) < 4:
        return []

    rates = [engagement_metrics(v)["views_per_day"] for v in uploads]
    sorted_rates = sorted(rates)
    n = len(sorted_rates)
    median = sorted_rates[n // 2] if n % 2 else (sorted_rates[n // 2 - 1] + sorted_rates[n // 2]) / 2
    mean = sum(rates) / n
    variance = sum((r - mean) ** 2 for r in rates) / n
    std_dev = variance ** 0.5 or 1

    anomalies = []
    for v, rate in zip(uploads, rates):
        z = (rate - mean) / std_dev
        if abs(z) >= 1.8:
            anomalies.append({
                "video_id": v.get("id"),
                "title": v.get("snippet", {}).get("title"),
                "views_per_day": round(rate, 1),
                "channel_median_views_per_day": round(median, 1),
                "z_score": round(z, 2),
                "direction": "spike" if z > 0 else "underperform",
            })

    return sorted(anomalies, key=lambda a: abs(a["z_score"]), reverse=True)


# --------------------------------------------------------------------------
# ANALYSE - misleading title/thumbnail detector
# --------------------------------------------------------------------------

MISLEADING_COMMENT_MARKERS = [
    "clickbait", "misleading", "click bait", "lied", "false advertising",
    "not what i expected", "waste of time", "didn't deliver", "did not deliver",
    "title is wrong", "nothing to do with", "false title",
]


def detect_misleading(video: dict, comment_texts: list[str]) -> dict:
    """Cross-checks a video's title against its own description/tags and
    against how commenters actually reacted. Three independent signals:

    1. Title/description keyword overlap - a title with almost no overlap
       with its own description is a mild red flag (may be over-selling).
    2. Title clickbait score (reused from the title generator).
    3. How many comments explicitly call it out as misleading/clickbait.
    """

    snippet = video.get("snippet", {})
    title = snippet.get("title", "")
    description = snippet.get("description", "")
    tags = snippet.get("tags", [])

    title_keywords = set(_extract_keywords(title))
    body_keywords = set(_extract_keywords(description)) | set(w.lower() for w in tags)
    overlap = len(title_keywords & body_keywords) / max(len(title_keywords), 1)

    title_score = score_title(title)

    normalized_comments = [c.lower() for c in comment_texts if c]
    flagged_comments = sum(
        1 for c in normalized_comments if any(marker in c for marker in MISLEADING_COMMENT_MARKERS)
    )
    comment_flag_pct = round(100 * flagged_comments / max(len(normalized_comments), 1), 1) if normalized_comments else 0.0

    # Weighted composite: comment reaction is the strongest signal (people
    # noticed and said so), clickbait phrasing next, keyword overlap weakest
    # (plenty of legitimate titles paraphrase rather than repeat keywords).
    misleading_score = round(
        min(100, comment_flag_pct * 3 + (100 - title_score["score"]) * 0.3 + (1 - overlap) * 20),
        1,
    )

    if misleading_score >= 60:
        verdict = "likely misleading"
    elif misleading_score >= 30:
        verdict = "some risk of overselling"
    else:
        verdict = "looks representative"

    return {
        "misleading_score": misleading_score,
        "verdict": verdict,
        "title_description_overlap_pct": round(overlap * 100, 1),
        "title_clickbait_risk": title_score["clickbait_risk"],
        "comments_flagging_misleading_pct": comment_flag_pct,
        "sample_size": len(normalized_comments),
    }


# --------------------------------------------------------------------------
# ANALYSE - sponsorship / brand-safety score
# --------------------------------------------------------------------------


def brand_safety_score(channel: dict, sampled_sentiments: list[dict], recent_videos: list[dict]) -> dict:
    """Rolls up toxicity, engagement quality and upload consistency into one
    score aimed at "would a brand feel safe sponsoring this channel"."""

    if sampled_sentiments:
        avg_toxicity = sum(s.get("toxicity_pct", 0) for s in sampled_sentiments) / len(sampled_sentiments)
        avg_positive = sum(s.get("overall_positive_pct", 0) for s in sampled_sentiments) / len(sampled_sentiments)
    else:
        avg_toxicity = 0.0
        avg_positive = 50.0

    avg_engagement = (
        sum(engagement_metrics(v)["engagement_rate_pct"] for v in recent_videos) / len(recent_videos)
        if recent_videos else 0.0
    )

    ages = sorted(_age_days(v.get("snippet", {}).get("publishedAt")) for v in recent_videos)
    gaps = [b - a for a, b in zip(ages, ages[1:])]
    consistency_penalty = min(20, (sum(gaps) / len(gaps)) * 0.5) if gaps else 10

    score = 100
    score -= avg_toxicity * 3
    score -= max(0, 40 - avg_positive) * 0.5
    score -= consistency_penalty
    score += min(10, avg_engagement * 2)
    score = round(max(0, min(100, score)), 1)

    strengths, risks = [], []
    if avg_toxicity < 5:
        strengths.append("low community toxicity")
    else:
        risks.append(f"elevated toxicity in sampled comments ({round(avg_toxicity, 1)}%)")
    if avg_positive > 50:
        strengths.append("majority-positive audience sentiment")
    else:
        risks.append("audience sentiment is not clearly positive")
    if avg_engagement > 2:
        strengths.append("above-average engagement rate")
    if consistency_penalty > 12:
        risks.append("inconsistent upload schedule")

    return {
        "brand_safety_score": score,
        "strengths": strengths,
        "risks": risks,
        "basis": {
            "avg_comment_toxicity_pct": round(avg_toxicity, 1),
            "avg_comment_positive_pct": round(avg_positive, 1),
            "avg_engagement_rate_pct": round(avg_engagement, 2),
            "sample_size_videos": len(sampled_sentiments),
        },
    }


# --------------------------------------------------------------------------
# ANALYSE - playlist intelligence
# --------------------------------------------------------------------------


def playlist_summary(videos: list[dict]) -> dict:
    if not videos:
        return {"video_count": 0}

    metrics = [engagement_metrics(v) for v in videos]
    views = [m["views"] for m in metrics]
    engagement_rates = [m["engagement_rate_pct"] for m in metrics]

    best_idx = max(range(len(videos)), key=lambda i: views[i])
    worst_idx = min(range(len(videos)), key=lambda i: views[i])

    mean_views = sum(views) / len(views)
    variance = sum((v - mean_views) ** 2 for v in views) / len(views)
    consistency_pct = round(100 * (1 - min(1, (variance ** 0.5) / max(mean_views, 1))), 1)

    return {
        "video_count": len(videos),
        "total_views": sum(views),
        "avg_views": round(mean_views, 1),
        "avg_engagement_rate_pct": round(sum(engagement_rates) / len(engagement_rates), 3),
        "consistency_pct": consistency_pct,
        "best_video": {"id": videos[best_idx].get("id"), "title": videos[best_idx].get("snippet", {}).get("title"), "views": views[best_idx]},
        "weakest_video": {"id": videos[worst_idx].get("id"), "title": videos[worst_idx].get("snippet", {}).get("title"), "views": views[worst_idx]},
    }


# --------------------------------------------------------------------------
# CREATE - personalized title insights from your own tracked-video history
# --------------------------------------------------------------------------


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = (var_x * var_y) ** 0.5
    return cov / denom if denom else 0.0


def personalized_title_insights(titles: list[str], virality_scores: list[float]) -> dict:
    """Correlates title characteristics with how your own tracked videos
    actually performed. Needs at least a handful of tracked videos with
    snapshot history to say anything meaningful."""

    if len(titles) < 4:
        return {
            "sample_size": len(titles),
            "insights": [],
            "note": "Need at least 4 tracked videos with history to compute correlations.",
        }

    lengths = [len(t) for t in titles]
    caps_ratios = [
        sum(1 for c in t if c.isupper()) / max(sum(1 for c in t if c.isalpha()), 1)
        for t in titles
    ]
    clickbait_hits = [sum(1 for m in CLICKBAIT_MARKERS if m in t.lower()) for t in titles]

    length_corr = _pearson(lengths, virality_scores)
    caps_corr = _pearson(caps_ratios, virality_scores)
    clickbait_corr = _pearson(clickbait_hits, virality_scores)

    insights = []
    if abs(length_corr) > 0.2:
        direction = "shorter" if length_corr < 0 else "longer"
        insights.append(f"Your {direction} titles tend to perform better (correlation {round(length_corr, 2)}).")
    if abs(caps_corr) > 0.2:
        direction = "less" if caps_corr < 0 else "more"
        insights.append(f"Titles with {direction} capitalization tend to perform better (correlation {round(caps_corr, 2)}).")
    if abs(clickbait_corr) > 0.2:
        direction = "fewer" if clickbait_corr < 0 else "more"
        insights.append(f"Titles with {direction} clickbait phrasing tend to perform better (correlation {round(clickbait_corr, 2)}).")
    if not insights:
        insights.append("No strong title-pattern correlation found yet in your history.")

    return {
        "sample_size": len(titles),
        "insights": insights,
        "correlations": {
            "length_vs_virality": round(length_corr, 3),
            "caps_ratio_vs_virality": round(caps_corr, 3),
            "clickbait_hits_vs_virality": round(clickbait_corr, 3),
        },
    }


# --------------------------------------------------------------------------
# DISCOVER - topic intelligence (product reviews, movie/trailer reactions)
# --------------------------------------------------------------------------

PURCHASE_INTENT_HIGH = ["buying it", "already ordered", "pre-ordered", "day one purchase", "definitely buying", "sold me"]
PURCHASE_INTENT_LOW = ["not buying", "waste of money", "skip this", "not worth it", "returning it", "cancelled my order"]
ANTICIPATION_MARKERS = ["can't wait", "cant wait", "hyped", "so excited", "day one", "counting down"]


def topic_intelligence_report(query: str, videos: list[dict], comment_texts_by_video: dict[str, list[str]], competitor_names: list[str] | None = None) -> dict:
    """One report across many videos matching a topic/product/movie name:
    aggregate sentiment, most-praised/most-criticised aspects, purchase-intent
    or anticipation signals, and competitor mention counts."""

    from app.services.youtube import sentiment as sentiment_engine

    all_texts: list[str] = []
    for texts in comment_texts_by_video.values():
        all_texts.extend(texts)

    overall_sentiment = sentiment_engine.aggregate_texts(all_texts)
    aspects = sentiment_engine.analyze_aspects(all_texts)

    praised = [a for a, v in aspects.items() if v["label"] == "positive"][:5]
    criticised = [a for a, v in aspects.items() if v["label"] == "negative"][:5]

    normalized = [t.lower() for t in all_texts if t]
    high_intent = sum(1 for t in normalized if any(m in t for m in PURCHASE_INTENT_HIGH))
    low_intent = sum(1 for t in normalized if any(m in t for m in PURCHASE_INTENT_LOW))
    anticipation_hits = sum(1 for t in normalized if any(m in t for m in ANTICIPATION_MARKERS))
    total = max(len(normalized), 1)

    competitor_mentions = {}
    for name in (competitor_names or []):
        competitor_mentions[name] = sum(1 for t in normalized if name.lower() in t)

    return {
        "query": query,
        "videos_analyzed": len(videos),
        "comments_analyzed": len(all_texts),
        "overall_sentiment": overall_sentiment,
        "most_praised_aspects": praised,
        "most_criticised_aspects": criticised,
        "purchase_intent": {
            "high_pct": round(100 * high_intent / total, 1),
            "low_pct": round(100 * low_intent / total, 1),
        },
        "anticipation_pct": round(100 * anticipation_hits / total, 1),
        "competitor_mentions": competitor_mentions,
    }


# --------------------------------------------------------------------------
# ANALYSE - channel audit (video portfolio evaluator)
# --------------------------------------------------------------------------


def channel_audit(channel: dict, recent_videos: list[dict], brand_safety: dict, upload_timing: dict, growth: dict) -> dict:
    """Combines existing signals (brand safety, upload timing, growth,
    thumbnail/title patterns from recent uploads) into one composite score
    with prioritized, actionable recommendations."""

    stats = channel.get("statistics", {})
    video_count = _stat_int(stats, "videoCount")
    subs = _stat_int(stats, "subscriberCount")

    title_scores = [score_title(v.get("snippet", {}).get("title", "")) for v in recent_videos]
    avg_title_score = sum(t["score"] for t in title_scores) / len(title_scores) if title_scores else 50
    clickbait_heavy = sum(1 for t in title_scores if t["clickbait_risk"] != "low")

    components = {
        "brand_safety_score": brand_safety.get("brand_safety_score", 50),
        "avg_title_score": round(avg_title_score, 1),
        "upload_consistency": 100 if upload_timing.get("sample_size", 0) >= 10 else 60,
    }
    overall = round(sum(components.values()) / len(components), 1)

    recommendations = []
    if clickbait_heavy > len(title_scores) * 0.3:
        recommendations.append("Reduce clickbait-style phrasing - over 30% of recent titles score risky.")
    if brand_safety.get("risks"):
        recommendations.extend(f"Address: {r}" for r in brand_safety["risks"][:2])
    if upload_timing.get("best_weekday"):
        recommendations.append(f"Your best-performing upload day is {upload_timing['best_weekday']} - stay consistent with it.")
    if video_count and subs and (subs / max(video_count, 1)) < 500:
        recommendations.append("Low subscribers-per-video ratio - consider focusing on fewer, higher-quality uploads.")
    if not recommendations:
        recommendations.append("No major issues found in the sampled signals - keep doing what's working.")

    return {
        "channel_intelligence_score": overall,
        "components": components,
        "recommendations": recommendations[:5],
    }


# --------------------------------------------------------------------------
# DISCOVER - semantic search (lite): TF-IDF re-ranking of YouTube's own
# results by meaning-similarity to the query, instead of raw relevance order.
# --------------------------------------------------------------------------


def semantic_rerank(query: str, items: list[dict]) -> list[dict]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    if not items:
        return []

    documents = [query] + [
        f"{item.get('snippet', {}).get('title', '')} {item.get('snippet', {}).get('description', '')}"
        for item in items
    ]

    vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    try:
        matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return items  # e.g. query is pure stopwords - fall back to original order

    similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    ranked = sorted(zip(items, similarities), key=lambda pair: pair[1], reverse=True)

    return [
        {**item, "semantic_similarity": round(float(score), 3)}
        for item, score in ranked
    ]


def cluster_comment_topics(comment_texts: list[str], n_clusters: int = 5) -> list[dict]:
    """Groups an already-fetched batch of comment text into topic clusters
    via TF-IDF + k-means, labelled by each cluster's top terms. Runs on
    comments already pulled for sentiment scoring - no extra API calls."""

    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer

    texts = [t for t in comment_texts if t and t.strip()]
    if len(texts) < n_clusters * 2:
        return []

    vectorizer = TfidfVectorizer(stop_words="english", max_features=500, min_df=2)
    try:
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return []  # e.g. every comment was pure stopwords/emoji

    k = min(n_clusters, len(texts) // 2) or 1
    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = model.fit_predict(matrix)

    terms = vectorizer.get_feature_names_out()
    topics = []
    for cluster_id in range(k):
        indices = [i for i, label in enumerate(labels) if label == cluster_id]
        if not indices:
            continue
        top_term_idx = model.cluster_centers_[cluster_id].argsort()[::-1][:5]
        top_terms = [terms[i] for i in top_term_idx]
        topics.append({
            "label": ", ".join(top_terms[:3]),
            "keywords": top_terms,
            "comment_count": len(indices),
            "sample_comment": texts[indices[0]][:140],
        })

    return sorted(topics, key=lambda t: t["comment_count"], reverse=True)


def upload_cadence(uploads: list[dict]) -> dict:
    """Which weekdays a channel actually publishes on, from its own
    recent-uploads list (already fetched for other Discover/Create
    features) - the publish-rhythm half of a channel comparison."""

    day_counts: dict[str, int] = {}
    for v in uploads:
        dt = _parse_dt(v.get("snippet", {}).get("publishedAt"))
        if not dt:
            continue
        day_counts[dt.strftime("%A")] = day_counts.get(dt.strftime("%A"), 0) + 1

    return {"uploads_by_weekday": day_counts, "sample_size": len(uploads)}
