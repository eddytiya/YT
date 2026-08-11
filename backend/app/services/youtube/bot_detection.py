"""
Fake-engagement RISK scoring, not proof.

Public API data cannot establish that engagement was purchased - only that
a video's comment/like/view pattern looks unusual relative to typical
organic behavior. Every output here is a signal-based risk score with the
detected patterns listed, so the caller can judge for themselves.
"""

import re
from collections import Counter
from datetime import datetime

_WORD_RE = re.compile(r"[a-z0-9']+")
PROMO_MARKERS = [
    "check out my channel", "sub for sub", "subscribe to my", "click my profile",
    "dm me", "whatsapp me", "telegram", "投资", "guaranteed profit", "crypto signal",
    "link in bio", "free followers", "free subscribers", "make money fast",
]


def _normalize(text: str) -> str:
    return " ".join(_WORD_RE.findall((text or "").lower()))


def _shingles(text: str, size: int = 4) -> set:
    words = text.split()
    if len(words) < size:
        return {text} if text else set()
    return {" ".join(words[i:i + size]) for i in range(len(words) - size + 1)}


def _similarity(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _flatten(item: dict) -> tuple[str, str, datetime | None]:
    snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
    text = snippet.get("textDisplay") or snippet.get("textOriginal") or ""
    author = snippet.get("authorDisplayName", "")
    published = snippet.get("publishedAt")
    try:
        dt = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None
    except ValueError:
        dt = None
    return text, author, dt


def analyze_engagement_risk(comment_threads: list[dict]) -> dict:
    parsed = [_flatten(item) for item in comment_threads]
    parsed = [(t, a, d) for t, a, d in parsed if t]

    if len(parsed) < 5:
        return {
            "risk_level": "unknown",
            "risk_score": 0,
            "sample_size": len(parsed),
            "patterns": [],
            "note": "Not enough comments sampled to assess engagement patterns.",
        }

    texts = [_normalize(t) for t, _, _ in parsed]
    shingle_sets = [_shingles(t) for t in texts]

    # Near-duplicate detection: pairwise shingle overlap above threshold.
    near_duplicates = 0
    checked = set()
    for i in range(len(shingle_sets)):
        for j in range(i + 1, len(shingle_sets)):
            if (i, j) in checked:
                continue
            checked.add((i, j))
            if _similarity(shingle_sets[i], shingle_sets[j]) > 0.6:
                near_duplicates += 1

    # Burst detection: many comments within a tight time window.
    timestamps = sorted(d for _, _, d in parsed if d)
    burst_windows = 0
    for i in range(len(timestamps)):
        window_end = i
        while window_end < len(timestamps) and (timestamps[window_end] - timestamps[i]).total_seconds() <= 240:
            window_end += 1
        if window_end - i >= 6:
            burst_windows += 1

    promo_hits = sum(1 for t, _, _ in parsed if any(m in t.lower() for m in PROMO_MARKERS))

    author_counts = Counter(a for _, a, _ in parsed if a)
    repeated_authors = sum(1 for _, count in author_counts.items() if count >= 3)

    patterns = []
    if near_duplicates > 0:
        patterns.append(f"{near_duplicates} near-duplicate comment pairs")
    if burst_windows > 0:
        patterns.append(f"{burst_windows} tight time-window comment bursts (6+ comments within 4 minutes)")
    if promo_hits > 0:
        patterns.append(f"{promo_hits} comments matching promotional/spam phrasing")
    if repeated_authors > 0:
        patterns.append(f"{repeated_authors} accounts posting 3+ times in this sample")

    total = len(parsed)
    risk_score = round(min(100, (
        (near_duplicates / max(total, 1)) * 150
        + (burst_windows / max(total, 1)) * 100
        + (promo_hits / max(total, 1)) * 120
        + (repeated_authors / max(total, 1)) * 80
    )), 1)

    if risk_score >= 50:
        risk_level = "high"
    elif risk_score >= 20:
        risk_level = "moderate"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "sample_size": total,
        "patterns": patterns,
        "note": "This is a heuristic risk signal from public comment data, not proof of purchased engagement.",
    }
